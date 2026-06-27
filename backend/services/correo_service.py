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
    pagos = comprobante.get("pagos") or []
    detalle_pagos = []
    if pagos:
        for i, p in enumerate(pagos, 1):
            detalle_pagos.append(
                f"  Pago {i}: {p.get('metodo_pago','')} - S/ {float(p.get('monto',0)):.2f}"
            )
            if p.get("numero_operacion"):
                detalle_pagos.append(f"           N° Op: {p['numero_operacion']}")
    else:
        detalle_pagos.append(f"  Metodo: {comprobante.get('metodo_pago','')}")
        detalle_pagos.append(f"  Monto:  S/ {float(comprobante.get('monto_pagado',0)):.2f}")

    precio_total = float(comprobante.get("precio_total") or comprobante.get("monto_pagado") or 0)

    mensaje.set_content(
        "\n".join([
            "Hotel Costa Azul",
            "",
            "Tu reserva fue confirmada correctamente.",
            f"Codigo de reserva: {comprobante['codigo_reserva']}",
            f"Habitacion: {comprobante['habitacion']}",
            f"Fechas: {comprobante['checkin']} al {comprobante['checkout']}",
            "",
            "DETALLE DE PAGOS:",
            *detalle_pagos,
            "",
            f"TOTAL PAGADO: S/ {precio_total:.2f}",
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
