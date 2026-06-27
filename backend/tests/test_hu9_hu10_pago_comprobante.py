"""
Tests HU9/HU10 — Pago y generación de comprobante
Cubre:
  - pagos_service: modo demo, validación de estados del proveedor
  - correo_service: modo demo SMTP, verificación de configuración
  - comprobantes_service: generación de PDF válido
  - POST /api/reservas/{codigo}/pago: validaciones de campos de tarjeta/transferencia
"""
import os
import unittest
from unittest.mock import MagicMock, patch
import json

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.comprobantes_service import generar_pdf_comprobante
from services.correo_service import smtp_configurado, demo_smtp_activo
from services.pagos_service import (
    proveedor_pago_configurado,
    demo_pagos_activo,
    _procesar_pago_demo,
)
from app import app


# ── COMPROBANTE PDF (HU10) ───────────────────────────────────────────────────

COMPROBANTE_FIXTURE = {
    "codigo_reserva": "RES-ABC123",
    "codigo_operacion": "OP-20260701120000",
    "cliente": "Luis Mendoza",
    "correo": "luis@test.com",
    "habitacion": "Suite - 301",
    "checkin": "2026-09-01",
    "checkout": "2026-09-05",
    "metodo_pago": "tarjeta",
    "monto_pagado": 1520.00,
    "fecha_pago": "2026-07-01T12:00:00",
    "estado_pago": "exitoso",
    "estado_reserva": "confirmada",
}


class TestHU10GenerarPDF(unittest.TestCase):

    def test_pdf_retorna_bytes(self):
        resultado = generar_pdf_comprobante(COMPROBANTE_FIXTURE)
        self.assertIsInstance(resultado, bytes)

    def test_pdf_comienza_con_cabecera_pdf(self):
        resultado = generar_pdf_comprobante(COMPROBANTE_FIXTURE)
        self.assertTrue(resultado.startswith(b"%PDF-"))

    def test_pdf_contiene_codigo_reserva(self):
        resultado = generar_pdf_comprobante(COMPROBANTE_FIXTURE)
        self.assertIn(b"RES-ABC123", resultado)

    def test_pdf_contiene_monto(self):
        resultado = generar_pdf_comprobante(COMPROBANTE_FIXTURE)
        self.assertIn(b"1520.00", resultado)

    def test_pdf_contiene_metodo_pago(self):
        resultado = generar_pdf_comprobante(COMPROBANTE_FIXTURE)
        self.assertIn(b"tarjeta", resultado)

    def test_pdf_no_vacio(self):
        resultado = generar_pdf_comprobante(COMPROBANTE_FIXTURE)
        self.assertGreater(len(resultado), 200)

    def test_pdf_termina_con_eof(self):
        resultado = generar_pdf_comprobante(COMPROBANTE_FIXTURE)
        self.assertIn(b"%%EOF", resultado)


# ── MODO DEMO SMTP (HU10) ────────────────────────────────────────────────────

class TestHU10CorreoServicio(unittest.TestCase):

    @patch.dict(os.environ, {"DEMO_SMTP": "true"})
    def test_demo_smtp_activo_cuando_env_true(self):
        self.assertTrue(demo_smtp_activo())

    @patch.dict(os.environ, {"DEMO_SMTP": "false"})
    def test_demo_smtp_inactivo_cuando_env_false(self):
        self.assertFalse(demo_smtp_activo())

    @patch.dict(os.environ, {"DEMO_SMTP": "true"})
    def test_smtp_configurado_en_modo_demo(self):
        self.assertTrue(smtp_configurado())

    @patch.dict(os.environ, {
        "DEMO_SMTP": "false",
        "SMTP_HOST": "",
        "SMTP_PORT": "",
        "SMTP_USER": "",
        "SMTP_PASSWORD": "",
        "SMTP_FROM": "",
    })
    def test_smtp_no_configurado_sin_vars_y_sin_demo(self):
        self.assertFalse(smtp_configurado())

    @patch.dict(os.environ, {"DEMO_SMTP": "true"})
    def test_enviar_correo_demo_no_lanza_excepcion(self):
        from services.correo_service import enviar_confirmacion_reserva
        # En modo demo no debe lanzar excepción ni intentar conectar SMTP
        try:
            enviar_confirmacion_reserva("test@test.com", COMPROBANTE_FIXTURE)
        except Exception as e:
            self.fail(f"enviar_confirmacion_reserva lanzó excepción en modo demo: {e}")


# ── MODO DEMO PAGOS (HU9) ────────────────────────────────────────────────────

class TestHU9PagosServicio(unittest.TestCase):

    @patch.dict(os.environ, {"DEMO_PAGOS": "true"})
    def test_demo_pagos_activo_cuando_env_true(self):
        self.assertTrue(demo_pagos_activo())

    @patch.dict(os.environ, {"DEMO_PAGOS": "false"})
    def test_demo_pagos_inactivo_cuando_env_false(self):
        self.assertFalse(demo_pagos_activo())

    @patch.dict(os.environ, {"DEMO_PAGOS": "true"})
    def test_proveedor_configurado_en_modo_demo(self):
        self.assertTrue(proveedor_pago_configurado())

    def test_pago_demo_retorna_estado_exitoso_o_rechazado(self):
        reserva = {
            "codigo_reserva": "RES-TEST01",
            "precio_total": 360.00,
            "nombre_cliente": "Luis",
            "apellido_cliente": "Mendoza",
            "correo_cliente": "luis@test.com",
            "dni_cliente": "45678901",
            "telefono_cliente": "987654321",
            "tipo_habitacion": "Simple",
            "numero_habitacion": "101",
            "fecha_checkin": "2026-09-01",
            "fecha_checkout": "2026-09-04",
        }
        resultado = _procesar_pago_demo(reserva, "tarjeta")
        self.assertIn(resultado["estado"], ("exitoso", "rechazado"))

    def test_pago_demo_retorna_transaction_id(self):
        reserva = {
            "codigo_reserva": "RES-TEST02",
            "precio_total": 200.00,
            "nombre_cliente": "Ana",
            "apellido_cliente": "García",
            "correo_cliente": "ana@test.com",
            "dni_cliente": "12345678",
            "telefono_cliente": "999888777",
            "tipo_habitacion": "Doble",
            "numero_habitacion": "201",
            "fecha_checkin": "2026-10-01",
            "fecha_checkout": "2026-10-03",
        }
        resultado = _procesar_pago_demo(reserva, "transferencia")
        self.assertIn("provider_transaction_id", resultado)
        self.assertTrue(resultado["provider_transaction_id"].startswith("DEMO-TXN-"))

    def test_pago_demo_mayoria_exitosos(self):
        """Estadísticamente, >70% de los pagos demo deben ser exitosos (expectativa: 90%)."""
        reserva = {
            "codigo_reserva": "RES-STAT",
            "precio_total": 100.00,
            "nombre_cliente": "Test", "apellido_cliente": "User",
            "correo_cliente": "t@t.com", "dni_cliente": "11111111",
            "telefono_cliente": "111111111",
            "tipo_habitacion": "Simple", "numero_habitacion": "001",
            "fecha_checkin": "2026-11-01", "fecha_checkout": "2026-11-02",
        }
        resultados = [_procesar_pago_demo(reserva, "tarjeta") for _ in range(100)]
        exitosos = sum(1 for r in resultados if r["estado"] == "exitoso")
        self.assertGreater(exitosos, 70)


# ── VALIDACIONES RUTA POST /pago ─────────────────────────────────────────────

class TestHU9ValidacionesPago(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    def test_metodo_invalido_retorna_400(self):
        resp = self.client.post(
            "/api/reservas/RES-TEST/pago",
            data=json.dumps({"metodo_pago": "criptomoneda"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("tarjeta o transferencia", resp.get_json()["error"])

    @patch.dict(os.environ, {"DEMO_PAGOS": "true", "DEMO_SMTP": "true"})
    @patch("routes.reservas.get_connection")
    @patch("routes.reservas.get_cursor")
    def test_numero_tarjeta_invalido_retorna_400(self, mock_get_cursor, mock_get_conn):
        mock_get_conn.return_value = MagicMock()
        mock_get_cursor.return_value = MagicMock()

        resp = self.client.post(
            "/api/reservas/RES-TEST/pago",
            data=json.dumps({
                "metodo_pago": "tarjeta",
                "titular": "Luis Mendoza",
                "numero_tarjeta": "123",  # muy corto
                "vencimiento": "12/27",
                "codigo_seguridad": "123",
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("digitos", resp.get_json()["error"])

    @patch.dict(os.environ, {"DEMO_PAGOS": "true", "DEMO_SMTP": "true"})
    @patch("routes.reservas.get_connection")
    @patch("routes.reservas.get_cursor")
    def test_vencimiento_formato_invalido_retorna_400(self, mock_get_cursor, mock_get_conn):
        mock_get_conn.return_value = MagicMock()
        mock_get_cursor.return_value = MagicMock()

        resp = self.client.post(
            "/api/reservas/RES-TEST/pago",
            data=json.dumps({
                "metodo_pago": "tarjeta",
                "titular": "Luis",
                "numero_tarjeta": "4111111111111111",
                "vencimiento": "2027/12",  # formato incorrecto
                "codigo_seguridad": "123",
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("MM/AA", resp.get_json()["error"])

    @patch.dict(os.environ, {"DEMO_PAGOS": "true", "DEMO_SMTP": "true"})
    @patch("routes.reservas.get_connection")
    @patch("routes.reservas.get_cursor")
    def test_operacion_transferencia_muy_corta_retorna_400(self, mock_get_cursor, mock_get_conn):
        mock_get_conn.return_value = MagicMock()
        mock_get_cursor.return_value = MagicMock()

        resp = self.client.post(
            "/api/reservas/RES-TEST/pago",
            data=json.dumps({
                "metodo_pago": "transferencia",
                "numero_operacion": "TRX",  # menos de 6 caracteres
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("6 caracteres", resp.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
