from datetime import datetime


def _pdf_escape(texto) -> str:
    return str(texto).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def generar_pdf_comprobante(comprobante: dict) -> bytes:
    lineas = [
        "Hotel Costa Azul",
        "Comprobante de pago",
        "",
        f"Reserva: {comprobante['codigo_reserva']}",
        f"Operacion: {comprobante['codigo_operacion']}",
        f"Cliente: {comprobante['cliente']}",
        f"Correo: {comprobante['correo']}",
        f"Habitacion: {comprobante['habitacion']}",
        f"Fechas: {comprobante['checkin']} al {comprobante['checkout']}",
        f"Metodo: {comprobante['metodo_pago']}",
        f"Monto: S/ {float(comprobante['monto_pagado']):.2f}",
        f"Fecha de pago: {comprobante['fecha_pago']}",
        f"Estado: {comprobante['estado_pago']}",
        "",
        f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]

    contenido = ["BT", "/F1 12 Tf", "72 760 Td", "16 TL"]
    for linea in lineas:
        contenido.append(f"({_pdf_escape(linea)}) Tj")
        contenido.append("T*")
    contenido.append("ET")
    stream = "\n".join(contenido).encode("latin-1", errors="replace")

    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for indice, objeto in enumerate(objetos, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{indice} 0 obj\n".encode("ascii"))
        pdf.extend(objeto)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objetos) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)
