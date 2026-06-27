import random
import string
from datetime import date


def generar_codigo_reserva() -> str:
    sufijo = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"RES-{sufijo}"


def calcular_noches(checkin: date, checkout: date) -> int:
    return (checkout - checkin).days


def calcular_precio_total(precio_base: float, noches: int) -> float:
    return round(float(precio_base) * noches, 2)
