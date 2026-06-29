import os
import mercadopago


def mp_configurado() -> bool:
    return bool(os.getenv("MP_ACCESS_TOKEN"))


def crear_preferencia(reserva: dict, frontend_base_url: str) -> dict:
    """
    Crea una preferencia de pago en Mercado Pago y retorna init_point (URL de checkout).

    reserva debe contener:
        codigo_reserva, precio_total, nombre_cliente, apellido_cliente,
        correo_cliente, tipo_habitacion, numero_habitacion, fecha_checkin, fecha_checkout
    """
    sdk = mercadopago.SDK(os.getenv("MP_ACCESS_TOKEN"))

    codigo = reserva["codigo_reserva"]
    titulo = (
        f"Hotel Costa Azul — {reserva['tipo_habitacion']} Nro. {reserva['numero_habitacion']} "
        f"({reserva['fecha_checkin']} → {reserva['fecha_checkout']})"
    )

    preference_data = {
        "items": [
            {
                "title":      titulo,
                "quantity":   1,
                "unit_price": float(reserva["precio_total"]),
                "currency_id": "PEN",
            }
        ],
        "payer": {
            "name":    reserva.get("nombre_cliente", ""),
            "surname": reserva.get("apellido_cliente", ""),
            "email":   reserva.get("correo_cliente", ""),
        },
        "external_reference": codigo,
        "back_urls": {
            "success": f"{frontend_base_url}/pago.html?mp_status=approved&mp_codigo={codigo}",
            "failure": f"{frontend_base_url}/pago.html?mp_status=failure&mp_codigo={codigo}",
            "pending": f"{frontend_base_url}/pago.html?mp_status=pending&mp_codigo={codigo}",
        },
        "auto_return": "approved",
        "notification_url": f"{os.getenv('BACKEND_URL', '')}/api/mercadopago/webhook",
        "statement_descriptor": "Hotel Costa Azul",
    }

    resultado = sdk.preference().create(preference_data)
    respuesta = resultado.get("response", {})

    if resultado.get("status") not in (200, 201):
        raise RuntimeError(
            respuesta.get("message", "No se pudo crear la preferencia en Mercado Pago")
        )

    return {
        "preference_id": respuesta.get("id"),
        "init_point":    respuesta.get("init_point"),
        "sandbox_init_point": respuesta.get("sandbox_init_point"),
    }
