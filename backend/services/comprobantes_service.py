from datetime import datetime


def _pdf_escape(texto) -> str:
    return str(texto).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


_NOMBRE_METODO = {
    "efectivo":       "Efectivo",
    "yape":           "Yape",
    "plin":           "Plin",
    "tarjeta_credito":"Tarjeta Credito",
    "tarjeta_debito": "Tarjeta Debito",
    "transferencia":  "Transferencia",
    "tarjeta":        "Tarjeta",
}


def generar_pdf_comprobante(comprobante: dict) -> bytes:
    precio_total = float(
        comprobante.get("precio_total") or comprobante.get("monto_pagado") or 0
    )
    total_pagado = float(comprobante.get("monto_pagado") or precio_total)

    lineas = [
        "Hotel Costa Azul",
        "Comprobante de Pago",
        "",
        f"Reserva:    {comprobante['codigo_reserva']}",
        f"Operacion:  {comprobante.get('codigo_operacion', '')}",
        f"Cliente:    {comprobante['cliente']}",
        f"Correo:     {comprobante['correo']}",
        f"Habitacion: {comprobante['habitacion']}",
        f"Fechas:     {comprobante['checkin']} al {comprobante['checkout']}",
        "",
        "--- DETALLE DE PAGOS ---",
    ]

    pagos = comprobante.get("pagos") or []
    if pagos:
        for i, p in enumerate(pagos, 1):
            monto   = float(p.get("monto", 0))
            metodo  = _NOMBRE_METODO.get(p.get("metodo_pago", ""), p.get("metodo_pago", ""))
            cod_op  = p.get("codigo_operacion", "")
            lineas.append(f"  Pago {i}: {metodo} - S/ {monto:.2f}")
            if p.get("numero_operacion"):
                lineas.append(f"           Num. Op: {p['numero_operacion']}")
            if p.get("vuelto") and float(p["vuelto"]) > 0:
                lineas.append(f"           Vuelto:  S/ {float(p['vuelto']):.2f}")
            lineas.append(f"           Cod. Op: {cod_op}")
    else:
        metodo = _NOMBRE_METODO.get(
            comprobante.get("metodo_pago", ""), comprobante.get("metodo_pago", "")
        )
        lineas.append(f"  Metodo:    {metodo}")
        lineas.append(f"  Monto:     S/ {total_pagado:.2f}")
        lineas.append(f"  Cod. Op:   {comprobante.get('codigo_operacion', '')}")

    lineas += [
        "",
        f"TOTAL RESERVA: S/ {precio_total:.2f}",
        f"TOTAL PAGADO:  S/ {total_pagado:.2f}",
        f"Estado:        {comprobante.get('estado_reserva', 'confirmada')}",
        f"Estado pago:   {comprobante.get('estado_pago', 'exitoso')}",
        "",
        f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]

    contenido = ["BT", "/F1 11 Tf", "50 760 Td", "14 TL"]
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
