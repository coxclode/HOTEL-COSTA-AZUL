import os
import random
import requests


ESTADOS_EXITOSOS = {"approved", "succeeded", "success", "paid", "exitoso", "aprobado"}
ESTADOS_RECHAZADOS = {"declined", "rejected", "failed", "error", "rechazado", "denied"}


def demo_pagos_activo() -> bool:
    return os.getenv("DEMO_PAGOS", "false").lower() == "true"


def proveedor_pago_configurado() -> bool:
    return demo_pagos_activo() or bool(os.getenv("PAYMENT_API_URL") and os.getenv("PAYMENT_API_KEY"))


def _procesar_pago_demo(reserva: dict, metodo_pago: str) -> dict:
    """Simula respuesta de proveedor externo para entornos de demostración."""
    exito = random.random() < 0.9  # 90 % de éxito en modo demo
    tx_id = f"DEMO-TXN-{random.randint(100000, 999999)}"
    if exito:
        return {
            "estado": "exitoso",
            "provider_status": "approved",
            "provider_transaction_id": tx_id,
            "provider_response": {"mode": "demo", "status": "approved"},
            "message": "[DEMO] Pago aprobado simulado correctamente",
        }
    return {
        "estado": "rechazado",
        "provider_status": "declined",
        "provider_transaction_id": tx_id,
        "provider_response": {"mode": "demo", "status": "declined"},
        "message": "[DEMO] Pago rechazado simulado (10 % de probabilidad)",
    }


def procesar_pago_real(reserva: dict, metodo_pago: str, datos_pago: dict) -> dict:
    if not proveedor_pago_configurado():
        raise RuntimeError("Proveedor de pagos no configurado")
    if demo_pagos_activo():
        return _procesar_pago_demo(reserva, metodo_pago)

    payload = {
        "order_id": reserva["codigo_reserva"],
        "amount": float(reserva["precio_total"]),
        "currency": os.getenv("PAYMENT_CURRENCY", "PEN"),
        "payment_method": metodo_pago,
        "customer": {
            "name": f"{reserva['nombre_cliente']} {reserva['apellido_cliente']}",
            "email": reserva["correo_cliente"],
            "document": reserva["dni_cliente"],
            "phone": reserva["telefono_cliente"],
        },
        "metadata": {
            "hotel": "Hotel Costa Azul",
            "room": f"{reserva['tipo_habitacion']} - {reserva['numero_habitacion']}",
            "checkin": str(reserva["fecha_checkin"]),
            "checkout": str(reserva["fecha_checkout"]),
        },
        "payment_data": datos_pago,
    }

    headers = {
        "Authorization": f"Bearer {os.getenv('PAYMENT_API_KEY')}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    respuesta = requests.post(
        os.getenv("PAYMENT_API_URL"),
        json=payload,
        headers=headers,
        timeout=int(os.getenv("PAYMENT_TIMEOUT_SECONDS", "20")),
    )

    try:
        data = respuesta.json()
    except ValueError:
        data = {"raw_response": respuesta.text}

    if respuesta.status_code >= 500:
        raise RuntimeError("El proveedor de pagos no respondio correctamente")

    estado_proveedor = str(
        data.get("status")
        or data.get("estado")
        or data.get("payment_status")
        or ""
    ).lower()

    if respuesta.status_code >= 400 and estado_proveedor not in ESTADOS_RECHAZADOS:
        mensaje = data.get("message") or data.get("error") or "Pago rechazado por el proveedor"
        return {
            "estado": "rechazado",
            "provider_status": estado_proveedor or str(respuesta.status_code),
            "provider_transaction_id": data.get("id") or data.get("transaction_id"),
            "provider_response": data,
            "message": mensaje,
        }

    if estado_proveedor in ESTADOS_EXITOSOS:
        estado = "exitoso"
    elif estado_proveedor in ESTADOS_RECHAZADOS:
        estado = "rechazado"
    else:
        raise RuntimeError("Estado de pago no reconocido por el proveedor")

    return {
        "estado": estado,
        "provider_status": estado_proveedor,
        "provider_transaction_id": data.get("id") or data.get("transaction_id") or data.get("operation_id"),
        "provider_response": data,
        "message": data.get("message") or data.get("description") or "Pago procesado por proveedor externo",
    }
