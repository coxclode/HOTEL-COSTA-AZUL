"""
Tests HU2 — Buscar habitaciones disponibles
Cubre:
  - Validaciones de parámetros: checkin/checkout obligatorios, formato, checkout > checkin
  - Filtros: tipo, precio_min, precio_max, personas
  - Respuesta correcta con habitaciones disponibles
  - Detección de colisiones (subquery SQL verificada via execute call)
  - Respuesta vacía cuando no hay habitaciones
"""
import unittest
from unittest.mock import MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import app


HAB_SIMPLE = {
    "id_habitacion": 1,
    "numero": "101",
    "tipo": "Simple",
    "precio_base": 120.00,
    "descripcion": "Habitacion simple",
    "capacidad": 2,
    "imagen": None,
}
HAB_SUITE = {
    "id_habitacion": 5,
    "numero": "501",
    "tipo": "Suite",
    "precio_base": 380.00,
    "descripcion": "Suite ejecutiva",
    "capacidad": 4,
    "imagen": None,
}


def _mock_disponibles(habitaciones):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [dict(h) for h in habitaciones]
    return mock_conn, mock_cursor


class TestHU2ValidacionParametros(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    def test_sin_checkin_retorna_400(self):
        resp = self.client.get("/api/habitaciones/disponibles?checkout=2026-09-05&personas=1")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("obligatorios", resp.get_json()["error"])

    def test_sin_checkout_retorna_400(self):
        resp = self.client.get("/api/habitaciones/disponibles?checkin=2026-09-01&personas=1")
        self.assertEqual(resp.status_code, 400)

    def test_sin_fechas_retorna_400(self):
        resp = self.client.get("/api/habitaciones/disponibles?personas=2")
        self.assertEqual(resp.status_code, 400)

    def test_formato_fecha_invalido_retorna_400(self):
        resp = self.client.get(
            "/api/habitaciones/disponibles?checkin=01-09-2026&checkout=05-09-2026"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("YYYY-MM-DD", resp.get_json()["error"])

    def test_checkout_igual_checkin_retorna_400(self):
        resp = self.client.get(
            "/api/habitaciones/disponibles?checkin=2026-09-01&checkout=2026-09-01"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("posterior", resp.get_json()["error"])

    def test_checkout_antes_de_checkin_retorna_400(self):
        resp = self.client.get(
            "/api/habitaciones/disponibles?checkin=2026-09-05&checkout=2026-09-01"
        )
        self.assertEqual(resp.status_code, 400)

    def test_personas_cero_retorna_400(self):
        resp = self.client.get(
            "/api/habitaciones/disponibles?checkin=2026-09-01&checkout=2026-09-05&personas=0"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("mayor a cero", resp.get_json()["error"])

    def test_personas_negativas_retorna_400(self):
        resp = self.client.get(
            "/api/habitaciones/disponibles?checkin=2026-09-01&checkout=2026-09-05&personas=-1"
        )
        self.assertEqual(resp.status_code, 400)


class TestHU2ResultadoBusqueda(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    @patch("routes.habitaciones.get_connection")
    @patch("routes.habitaciones.get_cursor")
    def test_retorna_habitaciones_disponibles(self, mock_get_cursor, mock_get_conn):
        mock_conn, mock_cursor = _mock_disponibles([HAB_SIMPLE, HAB_SUITE])
        mock_get_conn.return_value = mock_conn
        mock_get_cursor.return_value = mock_cursor

        resp = self.client.get(
            "/api/habitaciones/disponibles?checkin=2026-09-01&checkout=2026-09-05&personas=1"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("habitaciones", data)
        self.assertEqual(data["total"], 2)

    @patch("routes.habitaciones.get_connection")
    @patch("routes.habitaciones.get_cursor")
    def test_precio_base_como_float(self, mock_get_cursor, mock_get_conn):
        mock_conn, mock_cursor = _mock_disponibles([HAB_SIMPLE])
        mock_get_conn.return_value = mock_conn
        mock_get_cursor.return_value = mock_cursor

        resp = self.client.get(
            "/api/habitaciones/disponibles?checkin=2026-09-01&checkout=2026-09-05"
        )
        data = resp.get_json()
        hab = data["habitaciones"][0]
        self.assertIsInstance(hab["precio_base"], float)

    @patch("routes.habitaciones.get_connection")
    @patch("routes.habitaciones.get_cursor")
    def test_sin_resultados_devuelve_total_cero(self, mock_get_cursor, mock_get_conn):
        mock_conn, mock_cursor = _mock_disponibles([])
        mock_get_conn.return_value = mock_conn
        mock_get_cursor.return_value = mock_cursor

        resp = self.client.get(
            "/api/habitaciones/disponibles?checkin=2026-09-01&checkout=2026-09-05"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["total"], 0)
        self.assertEqual(resp.get_json()["habitaciones"], [])

    @patch("routes.habitaciones.get_connection")
    @patch("routes.habitaciones.get_cursor")
    def test_filtro_tipo_se_aplica_en_sql(self, mock_get_cursor, mock_get_conn):
        """Verifica que el parámetro tipo genere un filtro en la query SQL."""
        mock_conn, mock_cursor = _mock_disponibles([HAB_SIMPLE])
        mock_get_conn.return_value = mock_conn
        mock_get_cursor.return_value = mock_cursor

        self.client.get(
            "/api/habitaciones/disponibles"
            "?checkin=2026-09-01&checkout=2026-09-05&tipo=Simple"
        )
        # Verifica que el execute fue llamado con 'Simple' como parámetro
        execute_call = mock_cursor.execute.call_args
        parametros = execute_call[0][1]  # segundo argumento posicional
        self.assertIn("Simple", parametros)

    @patch("routes.habitaciones.get_connection")
    @patch("routes.habitaciones.get_cursor")
    def test_tipo_invalido_no_aplica_filtro(self, mock_get_cursor, mock_get_conn):
        """Tipo no válido no debe enviarse como filtro SQL (protección inyección)."""
        mock_conn, mock_cursor = _mock_disponibles([])
        mock_get_conn.return_value = mock_conn
        mock_get_cursor.return_value = mock_cursor

        self.client.get(
            "/api/habitaciones/disponibles"
            "?checkin=2026-09-01&checkout=2026-09-05&tipo=Presidencial"
        )
        execute_call = mock_cursor.execute.call_args
        parametros = execute_call[0][1]
        self.assertNotIn("Presidencial", parametros)

    @patch("routes.habitaciones.get_connection")
    @patch("routes.habitaciones.get_cursor")
    def test_colision_fechas_detectada_en_subquery(self, mock_get_cursor, mock_get_conn):
        """La query SQL debe incluir la subquery de colisión de fechas."""
        mock_conn, mock_cursor = _mock_disponibles([])
        mock_get_conn.return_value = mock_conn
        mock_get_cursor.return_value = mock_cursor

        self.client.get(
            "/api/habitaciones/disponibles?checkin=2026-09-01&checkout=2026-09-05"
        )
        sql_ejecutado = str(mock_cursor.execute.call_args[0][0])
        self.assertIn("NOT IN", sql_ejecutado)
        self.assertIn("fecha_checkin", sql_ejecutado)
        self.assertIn("fecha_checkout", sql_ejecutado)

    @patch("routes.habitaciones.get_connection")
    @patch("routes.habitaciones.get_cursor")
    def test_estados_activos_excluidos_de_colision(self, mock_get_cursor, mock_get_conn):
        """La subquery de colisión debe excluir estados: pendiente, confirmada, en_hospedaje."""
        mock_conn, mock_cursor = _mock_disponibles([])
        mock_get_conn.return_value = mock_conn
        mock_get_cursor.return_value = mock_cursor

        self.client.get(
            "/api/habitaciones/disponibles?checkin=2026-09-01&checkout=2026-09-05"
        )
        sql_ejecutado = str(mock_cursor.execute.call_args[0][0])
        self.assertIn("pendiente", sql_ejecutado)
        self.assertIn("confirmada", sql_ejecutado)
        self.assertIn("en_hospedaje", sql_ejecutado)

    @patch("routes.habitaciones.get_connection")
    @patch("routes.habitaciones.get_cursor")
    def test_precio_min_se_aplica_en_parametros(self, mock_get_cursor, mock_get_conn):
        mock_conn, mock_cursor = _mock_disponibles([])
        mock_get_conn.return_value = mock_conn
        mock_get_cursor.return_value = mock_cursor

        self.client.get(
            "/api/habitaciones/disponibles"
            "?checkin=2026-09-01&checkout=2026-09-05&precio_min=100"
        )
        execute_call = mock_cursor.execute.call_args
        parametros = execute_call[0][1]
        self.assertIn(100.0, parametros)

    @patch("routes.habitaciones.get_connection")
    @patch("routes.habitaciones.get_cursor")
    def test_personas_se_filtra_por_capacidad(self, mock_get_cursor, mock_get_conn):
        """El parámetro personas debe filtrarse contra capacidad en la query."""
        mock_conn, mock_cursor = _mock_disponibles([])
        mock_get_conn.return_value = mock_conn
        mock_get_cursor.return_value = mock_cursor

        self.client.get(
            "/api/habitaciones/disponibles"
            "?checkin=2026-09-01&checkout=2026-09-05&personas=3"
        )
        execute_call = mock_cursor.execute.call_args
        parametros = execute_call[0][1]
        self.assertIn(3, parametros)


if __name__ == "__main__":
    unittest.main()
