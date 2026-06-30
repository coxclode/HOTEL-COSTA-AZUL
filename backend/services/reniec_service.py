"""
Servicio de consulta DNI con failover automático entre proveedores.

Patrón Strategy:
  ReniecProvider (ABC)
    ├── ReniecCloudProvider   → api.reniec.cloud    (gratuito, sin token)
    ├── ApisNetPeProvider     → apis.net.pe/v2      (requiere APIS_NET_PE_TOKEN)
    └── ApisPeruComProvider   → apisperu.com        (requiere APISPERU_TOKEN)

  ReniecService  ← único punto de acceso para el resto del sistema.

El orquestador intenta cada proveedor en orden; si uno falla (timeout,
HTTP error, respuesta inválida) pasa automáticamente al siguiente.
El cliente nunca interactúa con los proveedores directamente.
"""
from __future__ import annotations

import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

import requests as http_requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


# ── DTOs ─────────────────────────────────────────────────────────────────────

@dataclass
class DniData:
    """Respuesta normalizada de cualquier proveedor."""
    dni: str
    nombres: str
    apellido_paterno: str
    apellido_materno: str

    @property
    def nombre_completo(self) -> str:
        return " ".join(
            p for p in [self.nombres, self.apellido_paterno, self.apellido_materno] if p
        )

    def to_dict(self) -> dict:
        return {
            "dni":              self.dni,
            "nombres":          self.nombres,
            "apellido_paterno": self.apellido_paterno,
            "apellido_materno": self.apellido_materno,
            "nombre_completo":  self.nombre_completo,
            "verificado":       True,
        }


# ── Excepciones ───────────────────────────────────────────────────────────────

class ReniecError(Exception):
    """Raíz del árbol de excepciones RENIEC."""

class DniNoEncontrado(ReniecError):
    """El DNI no existe en ningún proveedor (404 confirmado)."""

class TodosLosProveedoresFallaron(ReniecError):
    """Ningún proveedor respondió exitosamente."""


# ── Sesión HTTP compartida con reintentos de red ──────────────────────────────

def _crear_sesion(reintentos: int = 2) -> http_requests.Session:
    """
    Crea una sesión requests con retry automático en errores de red
    (no en HTTP 4xx/5xx, que se manejan explícitamente en cada proveedor).
    """
    sesion  = http_requests.Session()
    retry   = Retry(
        total=reintentos,
        backoff_factor=0.4,
        status_forcelist=[],           # no reintentar en errores HTTP
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    sesion.mount("https://", adapter)
    sesion.mount("http://",  adapter)
    return sesion


# ── Interfaz base (Strategy) ──────────────────────────────────────────────────

class ReniecProvider(ABC):
    """Contrato que deben cumplir todos los proveedores."""

    name:        str = "base"
    timeout:     int = 8
    max_retries: int = 2

    def disponible(self) -> bool:
        """Override en proveedores que requieren credenciales."""
        return True

    @abstractmethod
    def _fetch(self, dni: str, sesion: http_requests.Session) -> DniData:
        """Realiza la llamada HTTP y devuelve DniData o lanza excepción."""

    def consultar(self, dni: str) -> Optional[DniData]:
        """
        Llama a _fetch con reintentos propios.
        - Retorna DniData si fue exitoso.
        - Relanza DniNoEncontrado sin reintentar.
        - Retorna None si todos los reintentos fallan.
        """
        sesion      = _crear_sesion(reintentos=self.max_retries)
        ultimo_error: Optional[Exception] = None

        for intento in range(1, self.max_retries + 1):
            try:
                return self._fetch(dni, sesion)
            except DniNoEncontrado:
                raise  # definitivo, no reintentar
            except Exception as exc:
                ultimo_error = exc
                logger.warning(
                    "[RENIEC] proveedor=%s intento=%d/%d dni=%s error=%s",
                    self.name, intento, self.max_retries, dni, exc,
                )
                if intento < self.max_retries:
                    time.sleep(0.4 * intento)

        logger.error(
            "[RENIEC] proveedor=%s agotó reintentos para dni=%s: %s",
            self.name, dni, ultimo_error,
        )
        return None


# ── Proveedor 1: api.reniec.cloud ────────────────────────────────────────────

class ReniecCloudProvider(ReniecProvider):
    """
    API gratuita sin autenticación.
    GET https://api.reniec.cloud/dni/{numero}
    Respuesta: { nombre, apellidoPaterno, apellidoMaterno, ... }
    """
    name = "reniec_cloud"

    def __init__(self) -> None:
        self.base_url = os.getenv("RENIEC_CLOUD_URL", "https://api.reniec.cloud/dni")

    def _fetch(self, dni: str, sesion: http_requests.Session) -> DniData:
        url = f"{self.base_url}/{dni}"
        try:
            resp = sesion.get(url, timeout=self.timeout, headers={"Accept": "application/json"})
        except http_requests.exceptions.Timeout as exc:
            raise TimeoutError(f"{self.name}: timeout") from exc
        except http_requests.exceptions.RequestException as exc:
            raise ConnectionError(f"{self.name}: error de red — {exc}") from exc

        if resp.status_code == 404:
            raise DniNoEncontrado(f"DNI {dni} no encontrado en {self.name}")
        if resp.status_code != 200:
            raise ConnectionError(f"{self.name}: HTTP {resp.status_code}")

        try:
            data = resp.json()
        except ValueError as exc:
            raise ValueError(f"{self.name}: respuesta no es JSON") from exc

        nombres = (data.get("nombre") or data.get("nombres") or "").strip().upper()
        ap      = (data.get("apellidoPaterno") or data.get("apellido_paterno") or "").strip().upper()
        am      = (data.get("apellidoMaterno") or data.get("apellido_materno") or "").strip().upper()

        if not nombres and not ap:
            raise ValueError(f"{self.name}: respuesta sin datos personales — {data}")

        return DniData(dni=dni, nombres=nombres, apellido_paterno=ap, apellido_materno=am)


# ── Proveedor 2: apis.net.pe/v2 ──────────────────────────────────────────────

class ApisNetPeProvider(ReniecProvider):
    """
    API con token de autenticación Bearer.
    GET https://api.apis.net.pe/v2/reniec/dni?numero={numero}
    Requiere: APIS_NET_PE_TOKEN
    """
    name = "apis_net_pe"

    def __init__(self) -> None:
        self.token   = os.getenv("APIS_NET_PE_TOKEN", "")
        self.api_url = os.getenv("APIS_NET_PE_RENIEC_URL", "https://api.apis.net.pe/v2/reniec/dni")

    def disponible(self) -> bool:
        return bool(self.token)

    def _fetch(self, dni: str, sesion: http_requests.Session) -> DniData:
        try:
            resp = sesion.get(
                self.api_url,
                params={"numero": dni},
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept":        "application/json",
                },
                timeout=self.timeout,
            )
        except http_requests.exceptions.Timeout as exc:
            raise TimeoutError(f"{self.name}: timeout") from exc
        except http_requests.exceptions.RequestException as exc:
            raise ConnectionError(f"{self.name}: error de red — {exc}") from exc

        if resp.status_code == 404:
            raise DniNoEncontrado(f"DNI {dni} no encontrado en {self.name}")
        if resp.status_code in (401, 403):
            raise PermissionError(f"{self.name}: token inválido o sin permisos")
        if resp.status_code != 200:
            raise ConnectionError(f"{self.name}: HTTP {resp.status_code}")

        try:
            data = resp.json()
        except ValueError as exc:
            raise ValueError(f"{self.name}: respuesta no es JSON") from exc

        # apis.net.pe devuelve {"message":"Token invalido"} con HTTP 200 cuando expira
        if data.get("message") and not data.get("nombres") and not data.get("apellidoPaterno"):
            raise PermissionError(f"{self.name}: {data['message']}")

        nombres = (data.get("nombres") or data.get("nombresCompletos") or "").strip().upper()
        ap      = (data.get("apellidoPaterno") or data.get("apellido_paterno") or "").strip().upper()
        am      = (data.get("apellidoMaterno") or data.get("apellido_materno") or "").strip().upper()

        if not nombres and not ap:
            raise ValueError(f"{self.name}: respuesta sin datos personales — {data}")

        return DniData(dni=dni, nombres=nombres, apellido_paterno=ap, apellido_materno=am)


# ── Proveedor 3: apisperu.com ─────────────────────────────────────────────────

class ApisPeruComProvider(ReniecProvider):
    """
    API alternativa con token por query param.
    GET https://dniruc.apisperu.com/api/v1/dni/{numero}?token={token}
    Requiere: APISPERU_TOKEN
    """
    name = "apisperu_com"

    def __init__(self) -> None:
        self.token   = os.getenv("APISPERU_TOKEN", "")
        self.api_url = os.getenv("APISPERU_DNI_URL", "https://dniruc.apisperu.com/api/v1/dni")

    def disponible(self) -> bool:
        return bool(self.token)

    def _fetch(self, dni: str, sesion: http_requests.Session) -> DniData:
        try:
            resp = sesion.get(
                f"{self.api_url}/{dni}",
                params={"token": self.token},
                timeout=self.timeout,
                headers={"Accept": "application/json"},
            )
        except http_requests.exceptions.Timeout as exc:
            raise TimeoutError(f"{self.name}: timeout") from exc
        except http_requests.exceptions.RequestException as exc:
            raise ConnectionError(f"{self.name}: error de red — {exc}") from exc

        if resp.status_code == 404:
            raise DniNoEncontrado(f"DNI {dni} no encontrado en {self.name}")
        if resp.status_code in (401, 403):
            raise PermissionError(f"{self.name}: token inválido")
        if resp.status_code != 200:
            raise ConnectionError(f"{self.name}: HTTP {resp.status_code}")

        try:
            data = resp.json()
        except ValueError as exc:
            raise ValueError(f"{self.name}: respuesta no es JSON") from exc

        nombres = (data.get("nombre") or data.get("nombres") or "").strip().upper()
        ap      = (data.get("apellidoPaterno") or "").strip().upper()
        am      = (data.get("apellidoMaterno") or "").strip().upper()

        if not nombres and not ap:
            raise ValueError(f"{self.name}: respuesta sin datos personales — {data}")

        return DniData(dni=dni, nombres=nombres, apellido_paterno=ap, apellido_materno=am)


# ── Servicio orquestador ──────────────────────────────────────────────────────

class ReniecService:
    """
    Único punto de acceso para consulta de DNI.
    Itera los proveedores en orden; si uno falla, pasa al siguiente.
    La lógica de failover es transparente para el llamador.
    """

    def __init__(self, providers: Optional[List[ReniecProvider]] = None) -> None:
        self._providers: List[ReniecProvider] = providers or [
            ApisNetPeProvider(),
        ]

    def consultar_dni(self, dni: str) -> DniData:
        """
        Consulta el DNI recorriendo proveedores en orden.
        Lanza:
          DniNoEncontrado           — el DNI no existe (confirmado)
          TodosLosProveedoresFallaron — ningún proveedor respondió
        """
        errores: list[str] = []

        for proveedor in self._providers:
            if not proveedor.disponible():
                logger.debug(
                    "[RENIEC] proveedor=%s omitido (credenciales no configuradas)",
                    proveedor.name,
                )
                continue

            try:
                resultado = proveedor.consultar(dni)
                if resultado is not None:
                    logger.info(
                        "[RENIEC] dni=%s verificado via proveedor=%s", dni, proveedor.name
                    )
                    return resultado
                errores.append(f"{proveedor.name}: sin resultado")
            except DniNoEncontrado:
                # Un proveedor confirmó que el DNI no existe → propagar
                raise
            except Exception as exc:
                errores.append(f"{proveedor.name}: {exc}")
                logger.warning(
                    "[RENIEC] proveedor=%s descartado para dni=%s: %s",
                    proveedor.name, dni, exc,
                )

        raise TodosLosProveedoresFallaron(
            f"Ningún proveedor pudo verificar el DNI {dni}. Errores: {errores}"
        )


# ── Singleton ─────────────────────────────────────────────────────────────────

_servicio: Optional[ReniecService] = None


def get_reniec_service() -> ReniecService:
    """Devuelve la instancia compartida de ReniecService."""
    global _servicio
    if _servicio is None:
        _servicio = ReniecService()
    return _servicio
