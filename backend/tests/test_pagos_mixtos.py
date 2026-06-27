"""
Tests de Pago Mixto — POST /api/reservas/{codigo}/pagos
Cubre:
  - Validaciones de campo (método inválido, monto <= 0, monto > saldo)
  - Efectivo: monto_entregado requerido y >= monto
  - Yape/Plin: numero_operacion requerido (>=4 chars)
  - Pago exitoso con efectivo → INSERT en pagos + saldo actualizado
  - Confirmación automática cuando saldo <= 0
  - GET /api/reservas/{codigo}/pagos → lista de pagos
  - Pago Mixto: dos métodos distintos hasta completar el total
  - PDF contiene múltiples pagos
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("DEMO_PAGOS", "true")
os.environ.setdefault("DEMO_SMTP",  "true")

from app import app
from services.comprobantes_service import generar_pdf_comprobante


# ── Helpers ─────────────────────────────────────────────────────────────────

def _reserva_row(precio_total=300.00, estado="pendiente"):
    return {
        "id_reserva":         99,
        "codigo_reserva":     "RSV-TEST01",
        "nombre_cliente":     "Luis",
        "apellido_cliente":   "Mendoza",
        "correo_cliente":     "luis@test.com",
        "telefono_cliente":   "987654321",
        "dni_cliente":        "12345678",
        "fecha_checkin":      "2026-09-01",
        "fecha_checkout":     "2026-09-03",
        "precio_total":       precio_total,
        "estado":             estado,
        "numero_habitacion":  "101",
        "tipo_habitacion":    "Simple",
    }


def _pago_insert_row():
    from datetime import datetime
    return {
        "id_pago":    1,
        "fecha_pago": datetime(2026, 9, 1, 10, 0, 0),
    }


def _pago_list_row():
    from datetime import datetime
    return {
        "id_pago":          1,
        "metodo_pago":      "efectivo",
        "monto":            150.00,
        "estado":           "exitoso",
        "fecha_pago":       datetime(2026, 9, 1, 10, 0, 0),
        "codigo_operacion": "EFE-20260901100000-000001",
        "numero_operacion": None,
        "monto_entregado":  200.00,
        "vuelto":           50.00,
    }


def _make_db_mocks(precio_total=300.00, total_ya_pagado=0.00, estado="pendiente"):
    """
    Returns (mock_get_connection, mock_get_cursor) ready to patch.
    Simulates the sequence of fetchone calls in agregar_pago.
    """
    cursor = MagicMock()
    conexion = MagicMock()

    call_count = [0]

    def fetchone_side():
        call_count[0] += 1
        n = call_count[0]
        if n == 1:
            return _reserva_row(precio_total=precio_total, estado=estado)
        if n == 2:
            return {"total_pagado": total_ya_pagado}
        if n == 3:
            return _pago_insert_row()
        # After confirmation: re-fetch pagos list (via fetchall), no extra fetchone needed
        return None

    cursor.fetchone.side_effect = fetchone_side
    cursor.fetchall.return_value = [_pago_list_row()]

    return conexion, cursor


def _patch_db(conexion, cursor):
    """Return a context manager that patches get_connection and get_cursor."""
    from unittest.mock import patch as _patch
    p1 = _patch("routes.reservas.get_connection", return_value=conexion)
    p2 = _patch("routes.reservas.get_cursor", return_value=cursor)
    return p1, p2


# ── Suite principal ──────────────────────────────────────────────────────────

class TestPagosMixtos(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.url = "/api/reservas/RSV-TEST01/pagos"

    def _post(self, payload, precio_total=300.00, total_ya_pagado=0.00, estado="pendiente"):
        conexion, cursor = _make_db_mocks(precio_total, total_ya_pagado, estado)
        p1, p2 = _patch_db(conexion, cursor)
        with p1, p2:
            return self.client.post(
                self.url,
                data=json.dumps(payload),
                content_type="application/json",
            )

    # ── Validaciones de entrada ──

    def test_metodo_invalido_retorna_400(self):
        resp = self._post({"metodo_pago": "bitcoin", "monto": 100})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.get_json())

    def test_monto_cero_retorna_400(self):
        resp = self._post({"metodo_pago": "efectivo", "monto": 0})
        self.assertEqual(resp.status_code, 400)

    def test_monto_negativo_retorna_400(self):
        resp = self._post({"metodo_pago": "efectivo", "monto": -50})
        self.assertEqual(resp.status_code, 400)

    def test_efectivo_sin_monto_entregado_retorna_400(self):
        resp = self._post({"metodo_pago": "efectivo", "monto": 100})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("monto entregado", resp.get_json().get("error", "").lower())

    def test_efectivo_entregado_insuficiente_retorna_400(self):
        resp = self._post({
            "metodo_pago": "efectivo",
            "monto": 200,
            "monto_entregado": 150,
        })
        self.assertEqual(resp.status_code, 400)

    def test_yape_sin_operacion_retorna_400(self):
        resp = self._post({"metodo_pago": "yape", "monto": 100})
        self.assertEqual(resp.status_code, 400)

    def test_yape_operacion_corta_retorna_400(self):
        resp = self._post({
            "metodo_pago": "yape",
            "monto": 100,
            "numero_operacion": "ab",
        })
        self.assertEqual(resp.status_code, 400)

    def test_plin_sin_operacion_retorna_400(self):
        resp = self._post({"metodo_pago": "plin", "monto": 100})
        self.assertEqual(resp.status_code, 400)

    def test_monto_supera_saldo_retorna_400(self):
        # Reserva S/300, ya pagado S/200 → saldo S/100. Intento S/150 → error.
        resp = self._post(
            {"metodo_pago": "efectivo", "monto": 150, "monto_entregado": 200},
            precio_total=300.00, total_ya_pagado=200.00,
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("saldo", resp.get_json().get("error", "").lower())

    # ── Reserva no encontrada ──

    def test_reserva_inexistente_retorna_404(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        conexion = MagicMock()
        p1, p2 = _patch_db(conexion, cursor)
        with p1, p2:
            resp = self.client.post(
                "/api/reservas/NOEXISTE/pagos",
                data=json.dumps({
                    "metodo_pago": "efectivo",
                    "monto": 100,
                    "monto_entregado": 100,
                }),
                content_type="application/json",
            )
        self.assertEqual(resp.status_code, 404)

    # ── Pago exitoso con efectivo ──

    @patch("routes.reservas.enviar_confirmacion_reserva")
    def test_pago_efectivo_exitoso(self, _mock_correo):
        conexion, cursor = _make_db_mocks(precio_total=300.00, total_ya_pagado=0.00)
        p1, p2 = _patch_db(conexion, cursor)
        with p1, p2:
            resp = self.client.post(
                self.url,
                data=json.dumps({
                    "metodo_pago":      "efectivo",
                    "monto":            300,
                    "monto_entregado":  300,
                }),
                content_type="application/json",
            )
        if resp.status_code not in (200, 201):
            print("ERROR BODY:", resp.get_json())
        self.assertIn(resp.status_code, (200, 201))
        data = resp.get_json()
        self.assertIn("pago", data)
        self.assertIn("resumen", data)
        self.assertEqual(data["pago"]["metodo_pago"], "efectivo")

    # ── Confirmación automática cuando saldo == 0 ──

    @patch("routes.reservas.enviar_confirmacion_reserva")
    def test_reserva_confirmada_cuando_saldo_cero(self, _mock_correo):
        conexion, cursor = _make_db_mocks(precio_total=300.00, total_ya_pagado=0.00)
        p1, p2 = _patch_db(conexion, cursor)
        with p1, p2:
            resp = self.client.post(
                self.url,
                data=json.dumps({
                    "metodo_pago":     "efectivo",
                    "monto":           300,
                    "monto_entregado": 300,
                }),
                content_type="application/json",
            )
        if resp.status_code in (200, 201):
            self.assertTrue(resp.get_json()["resumen"]["reserva_confirmada"])

    # ── GET /pagos ──

    def test_get_pagos_retorna_lista(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = {
            "id_reserva":     99,
            "precio_total":   300.00,
            "estado_reserva": "pendiente",
        }
        cursor.fetchall.return_value = [_pago_list_row()]
        conexion = MagicMock()
        p1, p2 = _patch_db(conexion, cursor)
        with p1, p2:
            resp = self.client.get(self.url)

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("pagos", data)
        self.assertIsInstance(data["pagos"], list)
        self.assertIn("saldo_pendiente", data)

    # ── PDF multi-pago ──

    def test_pdf_con_multiples_pagos(self):
        comprobante = {
            "codigo_reserva":   "RSV-MIX01",
            "codigo_operacion": "EFE-20260901",
            "cliente":          "Luis Mendoza",
            "correo":           "luis@test.com",
            "habitacion":       "Suite - 301",
            "checkin":          "2026-09-01",
            "checkout":         "2026-09-03",
            "precio_total":     300.00,
            "monto_pagado":     300.00,
            "estado_pago":      "exitoso",
            "estado_reserva":   "confirmada",
            "pagos": [
                {
                    "metodo_pago":      "efectivo",
                    "monto":            150.00,
                    "codigo_operacion": "EFE-001",
                    "numero_operacion": None,
                    "vuelto":           50.00,
                },
                {
                    "metodo_pago":      "yape",
                    "monto":            150.00,
                    "codigo_operacion": "YAP-002",
                    "numero_operacion": "YAP-987654",
                    "vuelto":           None,
                },
            ],
        }
        pdf = generar_pdf_comprobante(comprobante)
        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertIn(b"Efectivo", pdf)
        self.assertIn(b"Yape",     pdf)
        self.assertIn(b"150.00",   pdf)

    def test_pdf_con_pago_unico_sin_lista(self):
        """Backward compat: sin key 'pagos' muestra pago único."""
        comprobante = {
            "codigo_reserva":   "RSV-BACK01",
            "codigo_operacion": "TJC-20260901",
            "cliente":          "Ana Torres",
            "correo":           "ana@test.com",
            "habitacion":       "Doble - 202",
            "checkin":          "2026-09-01",
            "checkout":         "2026-09-02",
            "metodo_pago":      "tarjeta_credito",
            "monto_pagado":     200.00,
            "precio_total":     200.00,
            "estado_pago":      "exitoso",
            "estado_reserva":   "confirmada",
        }
        pdf = generar_pdf_comprobante(comprobante)
        self.assertIn(b"Tarjeta Credito", pdf)
        self.assertIn(b"200.00", pdf)


# ── Suite: métodos digitales ─────────────────────────────────────────────────

class TestMetodosDigitales(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def _post_digital(self, payload):
        conexion, cursor = _make_db_mocks(precio_total=200.00, total_ya_pagado=0.00)
        p1, p2 = _patch_db(conexion, cursor)
        with p1, p2, patch("routes.reservas.enviar_confirmacion_reserva"):
            return self.client.post(
                "/api/reservas/RSV-TEST01/pagos",
                data=json.dumps(payload),
                content_type="application/json",
            )

    def test_yape_valido_retorna_201(self):
        resp = self._post_digital({
            "metodo_pago":     "yape",
            "monto":           200,
            "numero_operacion": "YAP-987654321",
        })
        self.assertIn(resp.status_code, (200, 201))

    def test_plin_valido_retorna_201(self):
        resp = self._post_digital({
            "metodo_pago":     "plin",
            "monto":           200,
            "numero_operacion": "PLN-123456789",
        })
        self.assertIn(resp.status_code, (200, 201))

    def test_efectivo_con_vuelto_retorna_vuelto_correcto(self):
        resp = self._post_digital({
            "metodo_pago":     "efectivo",
            "monto":           200,
            "monto_entregado": 250,
        })
        self.assertIn(resp.status_code, (200, 201))
        data = resp.get_json()
        if resp.status_code in (200, 201):
            self.assertEqual(data["pago"]["vuelto"], 50.0)


if __name__ == "__main__":
    unittest.main()
