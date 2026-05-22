import unittest

from habitaciones_service import filtrar_habitaciones_para_reserva


class HabitacionesParaReservaTest(unittest.TestCase):
    def test_descarta_habitaciones_bloqueadas(self):
        habitaciones = [
            {"numero": "101", "estado": "Disponible"},
            {"numero": "102", "estado": "Bloqueada"},
            {"numero": "103", "estado": "Mantenimiento"},
        ]

        resultado = filtrar_habitaciones_para_reserva(habitaciones)

        self.assertEqual(
            [habitacion["numero"] for habitacion in resultado],
            ["101", "103"],
        )
        self.assertNotIn(
            "Bloqueada",
            [habitacion["estado"] for habitacion in resultado],
        )


if __name__ == "__main__":
    unittest.main()
