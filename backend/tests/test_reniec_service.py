"""
Tests para ReniecService — consulta DNI con failover automático.

Cubre:
  1. Consulta exitosa con proveedor principal (reniec_cloud).
  2. Failover automático a proveedor secundario cuando el principal falla.
  3. Failover automático a proveedor terciario cuando los dos primeros fallan.
  4. Manejo de timeout en cualquier proveedor.
  5. Manejo de errores HTTP (4xx, 5xx).
  6. DNI inexistente (404 confirmado).
  7. DNI con formato inválido (validación en el controlador).
  8. Todos los proveedores caídos → TodosLosProveedoresFallaron.
  9. Respuesta con datos incompletos → failover al siguiente.
 10. Proveedor sin credenciales → se omite automáticamente.
 11. Endpoint GET /api/dni/<dni> — integración controlador ↔ servicio.
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("DEMO_PAGOS", "true")
os.environ.setdefault("DEMO_SMTP",  "true")

from services.reniec_service import (
    ReniecService,
    ReniecCloudProvider,
    ApisNetPeProvider,
    ApisPeruComProvider,
    DniData,
    DniNoEncontrado,
    TodosLosProveedoresFallaron,
)
from app import app


# ── Fixtures ─────────────────────────────────────────────────────────────────

DNI_VALIDO   = "76239564"
DNI_INVALIDO = "1234"

DATOS_MOCK = DniData(
    dni="76239564",
    nombres="JORGE LUIS",
    apellido_paterno="MENDOZA",
    apellido_materno="AVILA",
)


def _proveedor_exitoso(nombre="mock_ok") -> MagicMock:
    p = MagicMock(spec=ReniecCloudProvider)
    p.name       = nombre
    p.disponible = MagicMock(return_value=True)
    p.consultar  = MagicMock(return_value=DATOS_MOCK)
    return p


def _proveedor_fallido(nombre="mock_fail", exc=ConnectionError("sin red")) -> MagicMock:
    p = MagicMock(spec=ReniecCloudProvider)
    p.name       = nombre
    p.disponible = MagicMock(return_value=True)
    p.consultar  = MagicMock(side_effect=exc)
    return p


def _proveedor_sin_credenciales(nombre="mock_nocred") -> MagicMock:
    p = MagicMock(spec=ApisNetPeProvider)
    p.name       = nombre
    p.disponible = MagicMock(return_value=False)
    return p


# ══════════════════════════════════════════════════════════════════════════════
# 1. DniData
# ══════════════════════════════════════════════════════════════════════════════

class TestDniData(unittest.TestCase):

    def test_nombre_completo(self):
        self.assertEqual(DATOS_MOCK.nombre_completo, "JORGE LUIS MENDOZA AVILA")

    def test_to_dict_contiene_verificado(self):
        d = DATOS_MOCK.to_dict()
        self.assertTrue(d["verificado"])
        self.assertEqual(d["dni"], "76239564")
        self.assertEqual(d["nombres"], "JORGE LUIS")

    def test_nombre_completo_sin_apellido_materno(self):
        datos = DniData(dni="12345678", nombres="PEDRO", apellido_paterno="GARCIA", apellido_materno="")
        self.assertEqual(datos.nombre_completo, "PEDRO GARCIA")


# ══════════════════════════════════════════════════════════════════════════════
# 2. ReniecService — lógica de orquestación
# ══════════════════════════════════════════════════════════════════════════════

class TestReniecService(unittest.TestCase):

    # ── 2.1 Proveedor principal responde ──

    def test_retorna_datos_del_primer_proveedor(self):
        svc = ReniecService(providers=[_proveedor_exitoso("p1")])
        resultado = svc.consultar_dni(DNI_VALIDO)
        self.assertEqual(resultado.dni, DNI_VALIDO)
        self.assertEqual(resultado.nombres, "JORGE LUIS")

    # ── 2.2 Failover a proveedor secundario ──

    def test_failover_a_segundo_cuando_primero_falla(self):
        p1 = _proveedor_fallido("p1")
        p2 = _proveedor_exitoso("p2")
        svc = ReniecService(providers=[p1, p2])
        resultado = svc.consultar_dni(DNI_VALIDO)
        self.assertEqual(resultado.nombres, "JORGE LUIS")
        p1.consultar.assert_called_once_with(DNI_VALIDO)
        p2.consultar.assert_called_once_with(DNI_VALIDO)

    # ── 2.3 Failover a proveedor terciario ──

    def test_failover_a_tercero_cuando_primeros_dos_fallan(self):
        p1 = _proveedor_fallido("p1")
        p2 = _proveedor_fallido("p2")
        p3 = _proveedor_exitoso("p3")
        svc = ReniecService(providers=[p1, p2, p3])
        resultado = svc.consultar_dni(DNI_VALIDO)
        self.assertEqual(resultado.nombres, "JORGE LUIS")
        p3.consultar.assert_called_once_with(DNI_VALIDO)

    # ── 2.4 Timeout ──

    def test_timeout_hace_failover(self):
        p1 = _proveedor_fallido("p1", exc=TimeoutError("timeout"))
        p2 = _proveedor_exitoso("p2")
        svc = ReniecService(providers=[p1, p2])
        resultado = svc.consultar_dni(DNI_VALIDO)
        self.assertIsNotNone(resultado)

    # ── 2.5 Error HTTP ──

    def test_error_http_hace_failover(self):
        p1 = _proveedor_fallido("p1", exc=ConnectionError("HTTP 500"))
        p2 = _proveedor_exitoso("p2")
        svc = ReniecService(providers=[p1, p2])
        resultado = svc.consultar_dni(DNI_VALIDO)
        self.assertEqual(resultado.nombres, "JORGE LUIS")

    # ── 2.6 DNI inexistente ──

    def test_dni_no_encontrado_lanza_excepcion(self):
        p1 = _proveedor_fallido("p1", exc=DniNoEncontrado("DNI no existe"))
        svc = ReniecService(providers=[p1])
        with self.assertRaises(DniNoEncontrado):
            svc.consultar_dni("00000000")

    def test_dni_no_encontrado_no_intenta_siguiente_proveedor(self):
        """Si el primer proveedor confirma 404, no se consulta el siguiente."""
        p1 = _proveedor_fallido("p1", exc=DniNoEncontrado("DNI no existe"))
        p2 = _proveedor_exitoso("p2")
        svc = ReniecService(providers=[p1, p2])
        with self.assertRaises(DniNoEncontrado):
            svc.consultar_dni("00000000")
        p2.consultar.assert_not_called()

    # ── 2.7 Todos los proveedores caídos ──

    def test_todos_fallan_lanza_todos_fallaron(self):
        p1 = _proveedor_fallido("p1")
        p2 = _proveedor_fallido("p2")
        p3 = _proveedor_fallido("p3")
        svc = ReniecService(providers=[p1, p2, p3])
        with self.assertRaises(TodosLosProveedoresFallaron):
            svc.consultar_dni(DNI_VALIDO)

    def test_sin_proveedores_lanza_todos_fallaron(self):
        svc = ReniecService(providers=[])
        with self.assertRaises(TodosLosProveedoresFallaron):
            svc.consultar_dni(DNI_VALIDO)

    # ── 2.8 Proveedor sin credenciales se omite ──

    def test_proveedor_sin_credenciales_se_omite(self):
        sin_cred = _proveedor_sin_credenciales("p_nocred")
        p2       = _proveedor_exitoso("p2")
        svc = ReniecService(providers=[sin_cred, p2])
        resultado = svc.consultar_dni(DNI_VALIDO)
        self.assertEqual(resultado.nombres, "JORGE LUIS")
        sin_cred.consultar.assert_not_called()

    # ── 2.9 Datos incompletos → failover ──

    def test_respuesta_incompleta_hace_failover(self):
        """consultar() devuelve None cuando el proveedor retorna datos incompletos."""
        p1 = MagicMock(spec=ReniecCloudProvider)
        p1.name       = "p1_incompleto"
        p1.disponible = MagicMock(return_value=True)
        p1.consultar  = MagicMock(return_value=None)  # simula datos incompletos
        p2 = _proveedor_exitoso("p2")
        svc = ReniecService(providers=[p1, p2])
        resultado = svc.consultar_dni(DNI_VALIDO)
        self.assertEqual(resultado.nombres, "JORGE LUIS")


# ══════════════════════════════════════════════════════════════════════════════
# 3. ReniecCloudProvider — lógica interna
# ══════════════════════════════════════════════════════════════════════════════

class TestReniecCloudProvider(unittest.TestCase):

    def _mock_resp(self, status=200, json_body=None):
        resp = MagicMock()
        resp.status_code = status
        resp.json.return_value = json_body or {}
        return resp

    def _proveedor_con_sesion(self, resp):
        prov  = ReniecCloudProvider()
        sesion = MagicMock()
        sesion.get.return_value = resp
        return prov, sesion

    def test_fetch_exitoso(self):
        prov, sesion = self._proveedor_con_sesion(self._mock_resp(200, {
            "nombre": "JORGE LUIS",
            "apellidoPaterno": "MENDOZA",
            "apellidoMaterno": "AVILA",
        }))
        datos = prov._fetch(DNI_VALIDO, sesion)
        self.assertEqual(datos.nombres, "JORGE LUIS")
        self.assertEqual(datos.apellido_paterno, "MENDOZA")

    def test_fetch_404_lanza_dni_no_encontrado(self):
        prov, sesion = self._proveedor_con_sesion(self._mock_resp(404))
        with self.assertRaises(DniNoEncontrado):
            prov._fetch("00000000", sesion)

    def test_fetch_500_lanza_connection_error(self):
        prov, sesion = self._proveedor_con_sesion(self._mock_resp(500))
        with self.assertRaises(ConnectionError):
            prov._fetch(DNI_VALIDO, sesion)

    def test_fetch_timeout_lanza_timeout_error(self):
        import requests as req
        prov   = ReniecCloudProvider()
        sesion = MagicMock()
        sesion.get.side_effect = req.exceptions.Timeout()
        with self.assertRaises(TimeoutError):
            prov._fetch(DNI_VALIDO, sesion)

    def test_fetch_datos_incompletos_lanza_value_error(self):
        prov, sesion = self._proveedor_con_sesion(self._mock_resp(200, {"foo": "bar"}))
        with self.assertRaises(ValueError):
            prov._fetch(DNI_VALIDO, sesion)

    def test_disponible_siempre_true(self):
        self.assertTrue(ReniecCloudProvider().disponible())


# ══════════════════════════════════════════════════════════════════════════════
# 4. ApisNetPeProvider — lógica interna
# ══════════════════════════════════════════════════════════════════════════════

class TestApisNetPeProvider(unittest.TestCase):

    def setUp(self):
        os.environ["APIS_NET_PE_TOKEN"] = "test_token"

    def tearDown(self):
        os.environ.pop("APIS_NET_PE_TOKEN", None)

    def _mock_resp(self, status=200, json_body=None):
        resp = MagicMock()
        resp.status_code = status
        resp.json.return_value = json_body or {}
        return resp

    def test_fetch_exitoso(self):
        prov   = ApisNetPeProvider()
        sesion = MagicMock()
        sesion.get.return_value = self._mock_resp(200, {
            "nombres": "ANA LUCIA",
            "apellidoPaterno": "FLORES",
            "apellidoMaterno": "VEGA",
        })
        datos = prov._fetch(DNI_VALIDO, sesion)
        self.assertEqual(datos.nombres, "ANA LUCIA")

    def test_token_invalido_con_http_200_lanza_permission_error(self):
        """apis.net.pe devuelve HTTP 200 con {"message":"Token invalido"} cuando el token expiró."""
        prov   = ApisNetPeProvider()
        sesion = MagicMock()
        sesion.get.return_value = self._mock_resp(200, {"message": "Token invalido"})
        with self.assertRaises(PermissionError):
            prov._fetch(DNI_VALIDO, sesion)

    def test_401_lanza_permission_error(self):
        prov   = ApisNetPeProvider()
        sesion = MagicMock()
        sesion.get.return_value = self._mock_resp(401)
        with self.assertRaises(PermissionError):
            prov._fetch(DNI_VALIDO, sesion)

    def test_404_lanza_dni_no_encontrado(self):
        prov   = ApisNetPeProvider()
        sesion = MagicMock()
        sesion.get.return_value = self._mock_resp(404)
        with self.assertRaises(DniNoEncontrado):
            prov._fetch(DNI_VALIDO, sesion)

    def test_sin_token_no_disponible(self):
        os.environ.pop("APIS_NET_PE_TOKEN", None)
        prov = ApisNetPeProvider()
        self.assertFalse(prov.disponible())

    def test_con_token_disponible(self):
        self.assertTrue(ApisNetPeProvider().disponible())


# ══════════════════════════════════════════════════════════════════════════════
# 5. Endpoint GET /api/dni/<dni>
# ══════════════════════════════════════════════════════════════════════════════

class TestEndpointConsultarDni(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    # ── 5.1 Formato inválido ──

    def test_dni_corto_retorna_400(self):
        resp = self.client.get("/api/dni/1234")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.get_json())

    def test_dni_con_letras_retorna_400(self):
        resp = self.client.get("/api/dni/1234567A")
        self.assertEqual(resp.status_code, 400)

    def test_dni_de_9_digitos_retorna_400(self):
        resp = self.client.get("/api/dni/123456789")
        self.assertEqual(resp.status_code, 400)

    # ── 5.2 Consulta exitosa ──

    def test_consulta_exitosa_retorna_200(self):
        svc_mock = MagicMock()
        svc_mock.consultar_dni.return_value = DATOS_MOCK
        with patch("routes.reservas.get_reniec_service", return_value=svc_mock):
            resp = self.client.get(f"/api/dni/{DNI_VALIDO}")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["verificado"])
        self.assertEqual(data["nombres"], "JORGE LUIS")
        self.assertEqual(data["apellido_paterno"], "MENDOZA")

    # ── 5.3 DNI no encontrado ──

    def test_dni_no_encontrado_retorna_404(self):
        svc_mock = MagicMock()
        svc_mock.consultar_dni.side_effect = DniNoEncontrado("no existe")
        with patch("routes.reservas.get_reniec_service", return_value=svc_mock):
            resp = self.client.get("/api/dni/00000000")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("error", resp.get_json())

    # ── 5.4 Todos los proveedores fallaron ──

    def test_todos_proveedores_fallaron_retorna_503(self):
        svc_mock = MagicMock()
        svc_mock.consultar_dni.side_effect = TodosLosProveedoresFallaron("todos caídos")
        with patch("routes.reservas.get_reniec_service", return_value=svc_mock):
            resp = self.client.get(f"/api/dni/{DNI_VALIDO}")
        self.assertEqual(resp.status_code, 503)
        data = resp.get_json()
        self.assertIn("error", data)
        self.assertIn("detalle", data)

    # ── 5.5 Respuesta normalizada ──

    def test_respuesta_contiene_campos_esperados(self):
        svc_mock = MagicMock()
        svc_mock.consultar_dni.return_value = DATOS_MOCK
        with patch("routes.reservas.get_reniec_service", return_value=svc_mock):
            data = self.client.get(f"/api/dni/{DNI_VALIDO}").get_json()
        for campo in ["dni", "nombres", "apellido_paterno", "apellido_materno",
                      "nombre_completo", "verificado"]:
            self.assertIn(campo, data, f"Falta campo: {campo}")


if __name__ == "__main__":
    unittest.main()
