import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.habitaciones_service import filtrar_disponibles


class HU18HabitacionesServiceTest(unittest.TestCase):
    def test_descarta_habitaciones_bloqueadas(self):
        habitaciones = [
            {"numero": "101", "estado": "Disponible"},
            {"numero": "102", "estado": "Bloqueada"},
            {"numero": "103", "estado": "Mantenimiento"},
        ]

        resultado = filtrar_disponibles(habitaciones)

        numeros = [h["numero"] for h in resultado]
        self.assertEqual(numeros, ["101", "103"])
        self.assertNotIn("Bloqueada", [h["estado"] for h in resultado])

    def test_habitacion_disponible_no_se_descarta(self):
        habitaciones = [{"numero": "201", "estado": "Disponible"}]
        resultado = filtrar_disponibles(habitaciones)
        self.assertEqual(len(resultado), 1)

    def test_todas_bloqueadas_retorna_lista_vacia(self):
        habitaciones = [
            {"numero": "301", "estado": "Bloqueada"},
            {"numero": "302", "estado": "Bloqueada"},
        ]
        resultado = filtrar_disponibles(habitaciones)
        self.assertEqual(resultado, [])


if __name__ == "__main__":
    unittest.main()
