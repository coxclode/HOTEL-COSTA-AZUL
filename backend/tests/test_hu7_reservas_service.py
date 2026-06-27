"""
Tests HU7 — Generar reserva
Cubre:
  - reservas_service: generar_codigo, calcular_noches, calcular_precio_total
  - POST /api/reservas: validaciones de negocio (fechas, personas, colisiones)
  - Código único RES- generado correctamente
"""
import json
import unittest
from datetime import date
from unittest.mock import MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.reservas_service import (
    generar_codigo_reserva,
    calcular_noches,
    calcular_precio_total,
)
from app import app


# ── Tests de servicio puro ───────────────────────────────────────────────────

class TestReservasService(unittest.TestCase):

    # generar_codigo_reserva
    def test_codigo_comienza_con_RES(self):
        codigo = generar_codigo_reserva()
        self.assertTrue(codigo.startswith("RES-"))

    def test_codigo_longitud_correcta(self):
        codigo = generar_codigo_reserva()
        # "RES-" (4) + 6 chars = 10 total
        self.assertEqual(len(codigo), 10)

    def test_codigos_son_unicos(self):
        codigos = {generar_codigo_reserva() for _ in range(200)}
        # Con 200 muestras la probabilidad de colisión es ~0 %
        self.assertGreater(len(codigos), 195)

    # calcular_noches
    def test_noches_una_noche(self):
        noches = calcular_noches(date(2026, 7, 1), date(2026, 7, 2))
        self.assertEqual(noches, 1)

    def test_noches_cinco_noches(self):
        noches = calcular_noches(date(2026, 7, 1), date(2026, 7, 6))
        self.assertEqual(noches, 5)

    def test_noches_mismo_mes(self):
        noches = calcular_noches(date(2026, 8, 10), date(2026, 8, 25))
        self.assertEqual(noches, 15)

    def test_noches_cruce_mes(self):
        noches = calcular_noches(date(2026, 6, 28), date(2026, 7, 3))
        self.assertEqual(noches, 5)

    # calcular_precio_total
    def test_precio_total_simple(self):
        total = calcular_precio_total(120.00, 3)
        self.assertAlmostEqual(total, 360.00, places=2)

    def test_precio_total_una_noche(self):
        total = calcular_precio_total(380.00, 1)
        self.assertAlmostEqual(total, 380.00, places=2)

    def test_precio_total_redondeado_a_dos_decimales(self):
        total = calcular_precio_total(99.99, 3)
        self.assertAlmostEqual(total, 299.97, places=2)

    def test_precio_total_devuelve_float(self):
        total = calcular_precio_total(100, 2)
        self.assertIsInstance(total, float)


# ── Tests de ruta POST /api/reservas ────────────────────────────────────────

RESERVA_PAYLOAD_VALIDO = {
    "id_habitacion": 1,
    "nombre": "Luis",
    "apellido": "Mendoza",
    "dni": "45678901",
    "correo": "luis@test.com",
    "telefono": "987654321",
    "checkin": "2026-09-01",
    "checkout": "2026-09-05",
    "personas": 2,
}

HAB_BD = {
    "precio_base": 120.00,
    "estado": "Disponible",
    "capacidad": 3,
}


def _mock_db_reserva(sin_colision=True):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    # Primer fetchone → habitación
    # Segundo fetchone → COUNT(*) colisiones
    # Tercer fetchone → id_reserva después del INSERT
    colisiones_row = {"total": 0 if sin_colision else 1}
    id_row = {"id_reserva": 42}
    mock_cursor.fetchone.side_effect = [
        dict(HAB_BD),
        colisiones_row,
        id_row,
    ]
    mock_cursor.rowcount = 1
    return mock_conn, mock_cursor


class TestHU7CrearReservaRuta(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    @patch("routes.reservas.get_connection")
    @patch("routes.reservas.get_cursor")
    def test_crear_reserva_exitosa(self, mock_get_cursor, mock_get_conn):
        mock_conn, mock_cursor = _mock_db_reserva(sin_colision=True)
        mock_get_conn.return_value = mock_conn
        mock_get_cursor.return_value = mock_cursor

        resp = self.client.post(
            "/api/reservas",
            data=json.dumps(RESERVA_PAYLOAD_VALIDO),
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertIn("codigo_reserva", data)
        self.assertTrue(data["codigo_reserva"].startswith("RES-"))
        self.assertIn("precio_total", data)
        self.assertIn("noches", data)
        self.assertEqual(data["noches"], 4)

    def test_sin_id_habitacion_retorna_400(self):
        payload = dict(RESERVA_PAYLOAD_VALIDO)
        del payload["id_habitacion"]
        resp = self.client.post(
            "/api/reservas",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_checkout_igual_checkin_retorna_400(self):
        payload = {**RESERVA_PAYLOAD_VALIDO, "checkout": "2026-09-01"}
        resp = self.client.post(
            "/api/reservas",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("posterior", resp.get_json()["error"])

    def test_checkout_antes_checkin_retorna_400(self):
        payload = {**RESERVA_PAYLOAD_VALIDO, "checkout": "2026-08-25"}
        resp = self.client.post(
            "/api/reservas",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_personas_cero_retorna_400(self):
        # personas=-1 pasa la validación de campo obligatorio (es truthy)
        # pero falla en la validación de negocio "mayor a cero"
        payload = {**RESERVA_PAYLOAD_VALIDO, "personas": -1}
        resp = self.client.post(
            "/api/reservas",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("mayor a cero", resp.get_json()["error"])

    @patch("routes.reservas.get_connection")
    @patch("routes.reservas.get_cursor")
    def test_habitacion_bloqueada_retorna_409(self, mock_get_cursor, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "precio_base": 120.00,
            "estado": "Bloqueada",
            "capacidad": 3,
        }
        mock_get_conn.return_value = mock_conn
        mock_get_cursor.return_value = mock_cursor

        resp = self.client.post(
            "/api/reservas",
            data=json.dumps(RESERVA_PAYLOAD_VALIDO),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 409)
        self.assertIn("disponible", resp.get_json()["error"])

    @patch("routes.reservas.get_connection")
    @patch("routes.reservas.get_cursor")
    def test_personas_supera_capacidad_retorna_409(self, mock_get_cursor, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "precio_base": 120.00,
            "estado": "Disponible",
            "capacidad": 1,  # Solo 1 persona
        }
        mock_get_conn.return_value = mock_conn
        mock_get_cursor.return_value = mock_cursor

        payload = {**RESERVA_PAYLOAD_VALIDO, "personas": 3}
        resp = self.client.post(
            "/api/reservas",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 409)
        self.assertIn("capacidad", resp.get_json()["error"])

    @patch("routes.reservas.get_connection")
    @patch("routes.reservas.get_cursor")
    def test_colision_fechas_retorna_409(self, mock_get_cursor, mock_get_conn):
        mock_conn, mock_cursor = _mock_db_reserva(sin_colision=False)
        mock_get_conn.return_value = mock_conn
        mock_get_cursor.return_value = mock_cursor

        resp = self.client.post(
            "/api/reservas",
            data=json.dumps(RESERVA_PAYLOAD_VALIDO),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 409)
        self.assertIn("disponible en esas fechas", resp.get_json()["error"])

    @patch("routes.reservas.get_connection")
    @patch("routes.reservas.get_cursor")
    def test_estado_inicial_es_pendiente(self, mock_get_cursor, mock_get_conn):
        """Verifica que el INSERT incluya estado 'pendiente'."""
        mock_conn, mock_cursor = _mock_db_reserva(sin_colision=True)
        mock_get_conn.return_value = mock_conn
        mock_get_cursor.return_value = mock_cursor

        self.client.post(
            "/api/reservas",
            data=json.dumps(RESERVA_PAYLOAD_VALIDO),
            content_type="application/json",
        )

        # Verificar que se llamó execute con 'pendiente' en el INSERT
        calls = [str(call) for call in mock_cursor.execute.call_args_list]
        insert_call = next((c for c in calls if "INSERT INTO reservas" in c), None)
        self.assertIsNotNone(insert_call, "No se encontró INSERT INTO reservas")
        self.assertIn("pendiente", insert_call)


if __name__ == "__main__":
    unittest.main()
