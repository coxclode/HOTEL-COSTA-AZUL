"""
Tests HU15 — Gestionar habitaciones y precios
Cubre: CRUD completo + validaciones de negocio en rutas admin.
Estrategia: Flask test client + mocks de conexión BD (sin BD real).
"""
import json
import unittest
from unittest.mock import MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import app


# ── Helpers ─────────────────────────────────────────────────────────────────

HAB_FIXTURE = {
    "id_habitacion": 1,
    "numero": "101",
    "tipo": "Simple",
    "precio_base": 120.00,
    "descripcion": "Habitacion simple con baño privado",
    "estado": "Disponible",
    "capacidad": 2,
    "imagen": None,
}


def _mock_db(fetchall=None, fetchone=None, rowcount=1):
    """Devuelve mocks de conexión y cursor listos para usar."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = fetchall or []
    mock_cursor.fetchone.return_value = fetchone
    mock_cursor.rowcount = rowcount
    return mock_conn, mock_cursor


# ── Tests ────────────────────────────────────────────────────────────────────

class TestHU15ListarHabitaciones(unittest.TestCase):
    """GET /api/admin/habitaciones devuelve todas las habitaciones."""

    def setUp(self):
        self.client = app.test_client()

    @patch("routes.habitaciones.get_connection")
    @patch("routes.habitaciones.get_cursor")
    def test_listar_retorna_lista(self, mock_get_cursor, mock_get_conn):
        mock_conn, mock_cursor = _mock_db(fetchall=[dict(HAB_FIXTURE)])
        mock_get_conn.return_value = mock_conn
        mock_get_cursor.return_value = mock_cursor

        resp = self.client.get("/api/admin/habitaciones")

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("habitaciones", data)
        self.assertEqual(len(data["habitaciones"]), 1)
        self.assertEqual(data["habitaciones"][0]["numero"], "101")

    @patch("routes.habitaciones.get_connection")
    @patch("routes.habitaciones.get_cursor")
    def test_listar_devuelve_precio_como_float(self, mock_get_cursor, mock_get_conn):
        mock_conn, mock_cursor = _mock_db(fetchall=[dict(HAB_FIXTURE)])
        mock_get_conn.return_value = mock_conn
        mock_get_cursor.return_value = mock_cursor

        resp = self.client.get("/api/admin/habitaciones")
        data = resp.get_json()

        self.assertIsInstance(data["habitaciones"][0]["precio_base"], float)

    @patch("routes.habitaciones.get_connection")
    @patch("routes.habitaciones.get_cursor")
    def test_listar_lista_vacia(self, mock_get_cursor, mock_get_conn):
        mock_conn, mock_cursor = _mock_db(fetchall=[])
        mock_get_conn.return_value = mock_conn
        mock_get_cursor.return_value = mock_cursor

        resp = self.client.get("/api/admin/habitaciones")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["habitaciones"], [])


class TestHU15CrearHabitacion(unittest.TestCase):
    """POST /api/admin/habitaciones — crear habitación."""

    def setUp(self):
        self.client = app.test_client()

    @patch("routes.habitaciones.get_connection")
    @patch("routes.habitaciones.get_cursor")
    def test_crear_habitacion_exitosa(self, mock_get_cursor, mock_get_conn):
        mock_conn, mock_cursor = _mock_db(fetchone={"id_habitacion": 10})
        mock_get_conn.return_value = mock_conn
        mock_get_cursor.return_value = mock_cursor

        payload = {
            "numero": "201",
            "tipo": "Doble",
            "descripcion": "Habitacion doble con vista al jardin",
            "precio_base": 200.00,
            "capacidad": 3,
        }
        resp = self.client.post(
            "/api/admin/habitaciones",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertEqual(data["mensaje"], "Habitación registrada")
        self.assertEqual(data["id_habitacion"], 10)

    def test_crear_sin_numero_retorna_400(self):
        payload = {"tipo": "Simple", "descripcion": "Sin número"}
        resp = self.client.post(
            "/api/admin/habitaciones",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("obligatorios", resp.get_json()["error"])

    def test_crear_sin_tipo_retorna_400(self):
        payload = {"numero": "301", "descripcion": "Sin tipo"}
        resp = self.client.post(
            "/api/admin/habitaciones",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_crear_precio_negativo_retorna_400(self):
        payload = {
            "numero": "401",
            "tipo": "Suite",
            "descripcion": "Suite de prueba",
            "precio_base": -50,
        }
        resp = self.client.post(
            "/api/admin/habitaciones",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("negativo", resp.get_json()["error"].lower())

    def test_crear_capacidad_cero_retorna_400(self):
        payload = {
            "numero": "501",
            "tipo": "Simple",
            "descripcion": "Prueba",
            "precio_base": 100,
            "capacidad": 0,
        }
        resp = self.client.post(
            "/api/admin/habitaciones",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("capacidad", resp.get_json()["error"].lower())

    def test_crear_sin_descripcion_retorna_400(self):
        payload = {"numero": "601", "tipo": "Simple"}
        resp = self.client.post(
            "/api/admin/habitaciones",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)


class TestHU15EditarHabitacion(unittest.TestCase):
    """PUT /api/admin/habitaciones/{id} — editar habitación."""

    def setUp(self):
        self.client = app.test_client()

    @patch("routes.habitaciones.get_connection")
    @patch("routes.habitaciones.get_cursor")
    def test_editar_habitacion_exitoso(self, mock_get_cursor, mock_get_conn):
        mock_conn, mock_cursor = _mock_db(rowcount=1)
        mock_get_conn.return_value = mock_conn
        mock_get_cursor.return_value = mock_cursor

        payload = {
            "numero": "101",
            "tipo": "Doble",
            "descripcion": "Desc actualizada",
            "precio_base": 250.00,
            "capacidad": 4,
            "estado": "Disponible",
        }
        resp = self.client.put(
            "/api/admin/habitaciones/1",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["mensaje"], "Habitación actualizada")

    @patch("routes.habitaciones.get_connection")
    @patch("routes.habitaciones.get_cursor")
    def test_editar_habitacion_no_encontrada(self, mock_get_cursor, mock_get_conn):
        mock_conn, mock_cursor = _mock_db(rowcount=0)
        mock_get_conn.return_value = mock_conn
        mock_get_cursor.return_value = mock_cursor

        payload = {
            "numero": "999",
            "tipo": "Simple",
            "descripcion": "X",
            "precio_base": 100,
            "capacidad": 1,
            "estado": "Disponible",
        }
        resp = self.client.put(
            "/api/admin/habitaciones/9999",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 404)

    def test_editar_sin_campos_obligatorios_retorna_400(self):
        payload = {"numero": "101"}  # falta tipo, descripcion, estado
        resp = self.client.put(
            "/api/admin/habitaciones/1",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)


class TestHU15EliminarHabitacion(unittest.TestCase):
    """DELETE /api/admin/habitaciones/{id}."""

    def setUp(self):
        self.client = app.test_client()

    @patch("routes.habitaciones.get_connection")
    @patch("routes.habitaciones.get_cursor")
    def test_eliminar_exitoso(self, mock_get_cursor, mock_get_conn):
        mock_conn, mock_cursor = _mock_db(rowcount=1)
        mock_get_conn.return_value = mock_conn
        mock_get_cursor.return_value = mock_cursor

        resp = self.client.delete("/api/admin/habitaciones/1")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["mensaje"], "Habitación eliminada")

    @patch("routes.habitaciones.get_connection")
    @patch("routes.habitaciones.get_cursor")
    def test_eliminar_no_encontrado_retorna_404(self, mock_get_cursor, mock_get_conn):
        mock_conn, mock_cursor = _mock_db(rowcount=0)
        mock_get_conn.return_value = mock_conn
        mock_get_cursor.return_value = mock_cursor

        resp = self.client.delete("/api/admin/habitaciones/9999")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
