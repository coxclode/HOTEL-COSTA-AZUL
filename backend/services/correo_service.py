import os
import logging
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def demo_smtp_activo() -> bool:
    return os.getenv("DEMO_SMTP", "false").lower() == "true"


def smtp_configurado() -> bool:
    if demo_smtp_activo():
        return True
    obligatorios = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM"]
    return all(os.getenv(nombre) for nombre in obligatorios)


def enviar_confirmacion_reserva(destinatario: str, comprobante: dict) -> None:
    if not smtp_configurado():
        raise RuntimeError("Servicio SMTP no configurado")
    if demo_smtp_activo():
        logger.info(
            "[DEMO SMTP] Correo simulado a %s | Reserva: %s | Monto: S/ %.2f",
            destinatario,
            comprobante.get("codigo_reserva"),
            float(comprobante.get("monto_pagado", 0)),
        )
        return

    mensaje = EmailMessage()
    mensaje["Subject"] = f"Confirmacion de reserva {comprobante['codigo_reserva']}"
    mensaje["From"] = os.getenv("SMTP_FROM")
    mensaje["To"] = destinatario
    mensaje.set_content(
        "\n".join([
            "Hotel Costa Azul",
            "",
            "Tu reserva fue confirmada correctamente.",
            f"Codigo de reserva: {comprobante['codigo_reserva']}",
            f"Operacion de pago: {comprobante['codigo_operacion']}",
            f"Habitacion: {comprobante['habitacion']}",
            f"Fechas: {comprobante['checkin']} al {comprobante['checkout']}",
            f"Monto pagado: S/ {comprobante['monto_pagado']:.2f}",
            f"Metodo de pago: {comprobante['metodo_pago']}",
            "",
            "Conserva este correo para el check-in.",
        ])
    )

    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    usar_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    with smtplib.SMTP(host, port, timeout=15) as servidor:
        if usar_tls:
            servidor.starttls()
        servidor.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
        servidor.send_message(mensaje)
