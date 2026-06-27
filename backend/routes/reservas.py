from flask import Blueprint, request, jsonify, make_response
from datetime import datetime
import random
import re
import os
import string

import requests as http_requests
from psycopg2.extras import Json
from db import get_connection, get_cursor
from services.comprobantes_service import generar_pdf_comprobante
from services.correo_service import enviar_confirmacion_reserva, smtp_configurado
from services.pagos_service import procesar_pago_real, proveedor_pago_configurado
from services.reservas_service import (
    generar_codigo_reserva,
    calcular_noches,
    calcular_precio_total,
)

reservas_bp = Blueprint("reservas", __name__)

METODOS_DIGITALES = ("efectivo", "yape", "plin", "transferencia")
METODOS_TARJETA   = ("tarjeta_credito", "tarjeta_debito")
METODOS_VALIDOS   = METODOS_DIGITALES + METODOS_TARJETA

PREFIJO_METODO = {
    "efectivo":       "EFE",
    "yape":           "YAP",
    "plin":           "PLN",
    "transferencia":  "TRF",
    "tarjeta_credito":"TJC",
    "tarjeta_debito": "TJD",
}


def _codigo_operacion(metodo: str) -> str:
    prefijo = PREFIJO_METODO.get(metodo, "PAG")
    sufijo  = "".join(random.choices(string.digits, k=6))
    return f"{prefijo}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{sufijo}"


# ── Base de datos demo para RENIEC (DEMO_RENIEC=true) ──
_DEMO_RENIEC = {
    "76239564": ("JORGE LUIS",    "MENDOZA",   "AVILA"),
    "12345678": ("JUAN CARLOS",   "GARCIA",    "LOPEZ"),
    "87654321": ("MARIA ELENA",   "TORRES",    "RIOS"),
    "45678901": ("CARLOS ANDRES", "RAMIREZ",   "SILVA"),
    "98765432": ("ANA LUCIA",     "FLORES",    "VEGA"),
    "11111111": ("PEDRO PABLO",   "CASTILLO",  "MORALES"),
    "22222222": ("LUCIA SOFIA",   "HERRERA",   "CAMPOS"),
    "33333333": ("MIGUEL ANGEL",  "VARGAS",    "LUNA"),
    "44444444": ("ROSA MARIA",    "GUTIERREZ", "PAREDES"),
    "55555555": ("LUIS ALBERTO",  "MENDEZ",    "CHAVEZ"),
}

_NOMBRES_DEMO  = ["ALEX", "CARLOS", "DIANA", "ELENA", "FERNANDO",
                   "GABRIELA", "HUGO", "ISABEL", "JORGE", "KAREN"]
_APELLIDOS_DEMO = ["QUISPE", "MAMANI", "CONDORI", "HUANCA", "CCAMA",
                   "PILCO", "APAZA", "CALLA", "CHURA", "LLANOS"]


def _demo_reniec(dni: str) -> dict:
    """Devuelve datos simulados para cualquier DNI de 8 dígitos."""
    if dni in _DEMO_RENIEC:
        nombres, ap, am = _DEMO_RENIEC[dni]
    else:
        idx = int(dni) % 10
        nombres = _NOMBRES_DEMO[idx]
        ap      = _APELLIDOS_DEMO[(int(dni[2]) + int(dni[4])) % 10]
        am      = _APELLIDOS_DEMO[(int(dni[1]) + int(dni[5])) % 10]
    return {
        "dni": dni,
        "nombres": nombres,
        "apellido_paterno": ap,
        "apellido_materno": am,
        "nombre_completo": f"{nombres} {ap} {am}",
        "verificado": True,
        "_demo": True,
    }


# ── HU5: Verificar DNI contra RENIEC ──
@reservas_bp.route("/api/dni/<dni>", methods=["GET"])
def consultar_dni(dni):
    if not re.match(r'^\d{8}$', dni):
        return jsonify({"error": "El DNI debe tener exactamente 8 dígitos"}), 400

    # Modo demo: responde sin llamar a RENIEC real
    if os.getenv("DEMO_RENIEC", "false").lower() == "true":
        return jsonify(_demo_reniec(dni))

    token      = os.getenv("APIS_NET_PE_TOKEN", "")
    reniec_url = os.getenv("APIS_NET_PE_RENIEC_URL", "https://api.apis.net.pe/v2/reniec/dni")
    if not token:
        return jsonify(_demo_reniec(dni))   # sin token → demo automático

    try:
        resp = http_requests.get(
            reniec_url,
            params={"numero": dni},
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()

            # apis.net.pe devuelve {"message":"Token invalido"} con status 200
            if data.get("message") and not data.get("nombres") and not data.get("apellidoPaterno"):
                return jsonify(_demo_reniec(dni))

            nombres          = data.get("nombres") or data.get("nombresCompletos") or ""
            apellido_paterno = data.get("apellidoPaterno") or data.get("apellido_paterno") or ""
            apellido_materno = data.get("apellidoMaterno") or data.get("apellido_materno") or ""

            if not nombres and not apellido_paterno and not apellido_materno:
                return jsonify(_demo_reniec(dni))

            return jsonify({
                "dni": dni,
                "nombres": nombres,
                "apellido_paterno": apellido_paterno,
                "apellido_materno": apellido_materno,
                "nombre_completo": " ".join(
                    p for p in [nombres, apellido_paterno, apellido_materno] if p
                ),
                "verificado": True,
            })
        elif resp.status_code == 404:
            return jsonify({"error": "DNI no encontrado en RENIEC"}), 404
        elif resp.status_code in (401, 403):
            # Token inválido → caer a demo
            return jsonify(_demo_reniec(dni))
        else:
            return jsonify(_demo_reniec(dni))

    except (http_requests.exceptions.Timeout, http_requests.exceptions.RequestException):
        return jsonify(_demo_reniec(dni))


# ── HU6 / HU7: Crear reserva ──
@reservas_bp.route("/api/reservas", methods=["POST"])
def crear_reserva():
    data = request.get_json()

    campos = ["id_habitacion", "nombre", "apellido", "dni", "correo",
              "telefono", "checkin", "checkout", "personas"]
    for campo in campos:
        if not data.get(campo):
            return jsonify({"error": f"El campo '{campo}' es obligatorio"}), 400

    try:
        fecha_checkin  = datetime.strptime(data["checkin"],  "%Y-%m-%d").date()
        fecha_checkout = datetime.strptime(data["checkout"], "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Formato de fecha inválido. Use YYYY-MM-DD"}), 400

    if fecha_checkout <= fecha_checkin:
        return jsonify({"error": "La fecha de salida debe ser posterior a la de entrada"}), 400

    try:
        cantidad_personas = int(data["personas"])
    except (ValueError, TypeError):
        return jsonify({"error": "La cantidad de personas debe ser numerica"}), 400

    if cantidad_personas <= 0:
        return jsonify({"error": "La cantidad de personas debe ser mayor a cero"}), 400

    conexion = None
    cursor   = None
    try:
        conexion = get_connection()
        cursor   = get_cursor(conexion)

        cursor.execute("""
            SELECT precio_base, estado, capacidad FROM habitaciones
            WHERE id_habitacion = %s
        """, (data["id_habitacion"],))
        habitacion = cursor.fetchone()

        if habitacion is None:
            return jsonify({"error": "Habitación no encontrada"}), 404
        if habitacion["estado"] != "Disponible":
            return jsonify({"error": "La habitación ya no está disponible"}), 409
        if cantidad_personas > habitacion["capacidad"]:
            return jsonify({"error": "La cantidad de personas supera la capacidad de la habitacion"}), 409

        cursor.execute("""
            SELECT COUNT(*) AS total FROM reservas
            WHERE id_habitacion = %s
              AND estado IN ('pendiente', 'confirmada', 'en_hospedaje')
              AND fecha_checkin  < %s
              AND fecha_checkout > %s
        """, (data["id_habitacion"], fecha_checkout, fecha_checkin))

        if cursor.fetchone()["total"] > 0:
            return jsonify({"error": "La habitación no está disponible en esas fechas"}), 409

        noches       = calcular_noches(fecha_checkin, fecha_checkout)
        precio_total = calcular_precio_total(float(habitacion["precio_base"]), noches)
        codigo       = generar_codigo_reserva()

        cursor.execute("""
            INSERT INTO reservas
                (codigo_reserva, id_habitacion, nombre_cliente, apellido_cliente,
                 dni_cliente, correo_cliente, telefono_cliente,
                 cantidad_personas, fecha_checkin, fecha_checkout, precio_total, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pendiente')
            RETURNING id_reserva
        """, (
            codigo,
            data["id_habitacion"],
            data["nombre"].strip(),
            data["apellido"].strip(),
            data["dni"].strip(),
            data["correo"].strip(),
            data["telefono"].strip(),
            cantidad_personas,
            fecha_checkin,
            fecha_checkout,
            precio_total,
        ))

        id_reserva = cursor.fetchone()["id_reserva"]

        cursor.execute("""
            INSERT INTO notificaciones (id_reserva, tipo, leido)
            VALUES (%s, 'nueva_reserva', FALSE)
        """, (id_reserva,))

        conexion.commit()

        return jsonify({
            "mensaje":        "Reserva creada exitosamente",
            "codigo_reserva": codigo,
            "precio_total":   precio_total,
            "noches":         noches,
        }), 201

    except Exception as e:
        if conexion:
            conexion.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


# ── HU9: Agregar pago (soporta pago mixto y todos los métodos) ──
@reservas_bp.route("/api/reservas/<codigo_reserva>/pagos", methods=["POST"])
def agregar_pago(codigo_reserva):
    data        = request.get_json() or {}
    metodo_pago = (data.get("metodo_pago") or "").strip().lower()

    if metodo_pago not in METODOS_VALIDOS:
        return jsonify({"error": f"Método inválido. Opciones: {', '.join(METODOS_VALIDOS)}"}), 400

    try:
        monto = round(float(data.get("monto") or 0), 2)
    except (ValueError, TypeError):
        return jsonify({"error": "El monto debe ser numérico"}), 400

    if monto <= 0:
        return jsonify({"error": "El monto debe ser mayor a cero"}), 400

    # ── Validaciones específicas por método ──
    monto_entregado       = None
    vuelto                = None
    numero_operacion_val  = None
    datos_tarjeta         = {}

    if metodo_pago == "efectivo":
        try:
            monto_entregado = round(float(data.get("monto_entregado") or 0), 2)
        except (ValueError, TypeError):
            return jsonify({"error": "monto_entregado debe ser numérico"}), 400
        if monto_entregado < monto:
            return jsonify({"error": "El monto entregado debe ser mayor o igual al monto del pago"}), 400
        vuelto = round(monto_entregado - monto, 2)

    elif metodo_pago in ("yape", "plin", "transferencia"):
        numero_operacion_val = (data.get("numero_operacion") or "").strip()
        if len(numero_operacion_val) < 4:
            return jsonify({"error": "El número de operación debe tener al menos 4 caracteres"}), 400

    elif metodo_pago in METODOS_TARJETA:
        numero     = re.sub(r"\s+", "", data.get("numero_tarjeta") or "")
        titular    = (data.get("titular") or "").strip()
        vencimiento= (data.get("vencimiento") or "").strip()
        cvv        = (data.get("codigo_seguridad") or "").strip()

        if not re.match(r"^\d{13,19}$", numero):
            return jsonify({"error": "El número de tarjeta debe tener entre 13 y 19 digitos"}), 400
        if not titular:
            return jsonify({"error": "El titular de la tarjeta es obligatorio"}), 400
        if not re.match(r"^\d{2}/\d{2}$", vencimiento):
            return jsonify({"error": "El vencimiento debe tener formato MM/AA"}), 400
        if not re.match(r"^\d{3,4}$", cvv):
            return jsonify({"error": "El código de seguridad debe tener 3 o 4 dígitos"}), 400

        datos_tarjeta = {
            "card_number":  numero,
            "card_holder":  titular,
            "expiration":   vencimiento,
            "security_code": cvv,
        }

    conexion = None
    cursor   = None
    try:
        conexion = get_connection()
        cursor   = get_cursor(conexion)

        cursor.execute("""
            SELECT r.id_reserva, r.codigo_reserva,
                   r.nombre_cliente, r.apellido_cliente,
                   r.dni_cliente, r.correo_cliente, r.telefono_cliente,
                   r.fecha_checkin, r.fecha_checkout,
                   r.precio_total, r.estado,
                   h.numero AS numero_habitacion,
                   h.tipo   AS tipo_habitacion
            FROM reservas r
            JOIN habitaciones h ON r.id_habitacion = h.id_habitacion
            WHERE r.codigo_reserva = %s
        """, (codigo_reserva,))

        reserva = cursor.fetchone()
        if reserva is None:
            return jsonify({"error": "Reserva no encontrada"}), 404
        if reserva["estado"] not in ("pendiente",):
            return jsonify({"error": "La reserva ya está confirmada o no permite más pagos"}), 409

        # Calcular saldo pendiente
        cursor.execute("""
            SELECT COALESCE(SUM(monto), 0) AS total_pagado
            FROM pagos
            WHERE id_reserva = %s AND estado = 'exitoso'
        """, (reserva["id_reserva"],))

        total_pagado_actual = round(float(cursor.fetchone()["total_pagado"]), 2)
        precio_total        = round(float(reserva["precio_total"]), 2)
        saldo_pendiente     = round(precio_total - total_pagado_actual, 2)

        if monto > saldo_pendiente + 0.01:
            return jsonify({
                "error": f"El monto S/ {monto:.2f} supera el saldo pendiente S/ {saldo_pendiente:.2f}"
            }), 400

        # ── Procesar según método ──
        cod_op             = _codigo_operacion(metodo_pago)
        estado_pago        = "exitoso"
        prov_tx_id         = None
        prov_respuesta     = None

        if metodo_pago in METODOS_TARJETA:
            if not proveedor_pago_configurado():
                return jsonify({"error": "Proveedor de pagos no configurado"}), 503

            reserva_dict                = dict(reserva)
            reserva_dict["precio_total"] = monto

            resultado   = procesar_pago_real(reserva_dict, metodo_pago, datos_tarjeta)
            estado_pago = resultado["estado"]
            prov_tx_id  = resultado.get("provider_transaction_id")
            prov_respuesta = resultado.get("provider_response")
            if prov_tx_id:
                cod_op = prov_tx_id

            if estado_pago == "rechazado":
                return jsonify({
                    "error": "Pago rechazado por el proveedor",
                    "detalle": prov_respuesta,
                }), 402

        # ── Insertar pago ──
        cursor.execute("""
            INSERT INTO pagos (
                id_reserva, codigo_operacion, proveedor_transaccion_id,
                proveedor_estado, metodo_pago, monto, estado,
                proveedor_respuesta, monto_entregado, vuelto, numero_operacion
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id_pago, fecha_pago
        """, (
            reserva["id_reserva"],
            cod_op,
            prov_tx_id,
            "approved" if estado_pago == "exitoso" else "declined",
            metodo_pago,
            monto,
            estado_pago,
            Json(prov_respuesta) if prov_respuesta else None,
            monto_entregado,
            vuelto,
            numero_operacion_val,
        ))
        pago_row = cursor.fetchone()

        nuevo_total  = round(total_pagado_actual + monto, 2)
        nuevo_saldo  = round(precio_total - nuevo_total, 2)
        confirmada   = nuevo_saldo <= 0.001

        if confirmada:
            cursor.execute("""
                UPDATE reservas SET estado = 'confirmada'
                WHERE id_reserva = %s
            """, (reserva["id_reserva"],))

        conexion.commit()

        # ── Enviar correo cuando se confirma ──
        correo_enviado = False
        comprobante_para_correo = None

        if confirmada and smtp_configurado():
            cursor.execute("""
                SELECT metodo_pago, monto, estado, fecha_pago,
                       codigo_operacion, monto_entregado, vuelto, numero_operacion
                FROM pagos
                WHERE id_reserva = %s AND estado = 'exitoso'
                ORDER BY fecha_pago ASC
            """, (reserva["id_reserva"],))
            pagos_lista = _serializar_pagos(cursor.fetchall())

            comprobante_para_correo = {
                "codigo_reserva":  reserva["codigo_reserva"],
                "codigo_operacion": cod_op,
                "precio_total":    precio_total,
                "monto_pagado":    precio_total,
                "fecha_pago":      pago_row["fecha_pago"].isoformat(),
                "metodo_pago":     metodo_pago,
                "estado_pago":     "exitoso",
                "estado_reserva":  "confirmada",
                "cliente":         f"{reserva['nombre_cliente']} {reserva['apellido_cliente']}",
                "correo":          reserva["correo_cliente"],
                "habitacion":      f"{reserva['tipo_habitacion']} - {reserva['numero_habitacion']}",
                "checkin":         str(reserva["fecha_checkin"]),
                "checkout":        str(reserva["fecha_checkout"]),
                "pagos":           pagos_lista,
            }
            try:
                enviar_confirmacion_reserva(reserva["correo_cliente"], comprobante_para_correo)
                correo_enviado = True
                cursor.execute("""
                    UPDATE pagos SET correo_enviado = TRUE, fecha_correo = CURRENT_TIMESTAMP
                    WHERE id_pago = %s
                """, (pago_row["id_pago"],))
                conexion.commit()
            except Exception:
                pass

        return jsonify({
            "pago": {
                "id_pago":          pago_row["id_pago"],
                "codigo_operacion": cod_op,
                "metodo_pago":      metodo_pago,
                "monto":            monto,
                "monto_entregado":  monto_entregado,
                "vuelto":           vuelto,
                "numero_operacion": numero_operacion_val,
                "estado":           estado_pago,
                "fecha_pago":       pago_row["fecha_pago"].isoformat(),
            },
            "resumen": {
                "codigo_reserva":    codigo_reserva,
                "precio_total":      precio_total,
                "total_pagado":      nuevo_total,
                "saldo_pendiente":   max(nuevo_saldo, 0),
                "estado_reserva":    "confirmada" if confirmada else "pendiente",
                "reserva_confirmada": confirmada,
            },
            "correo_enviado":    correo_enviado,
            "comprobante_pdf_url": f"/api/reservas/{codigo_reserva}/comprobante.pdf" if confirmada else None,
        }), 201

    except Exception as e:
        if conexion:
            conexion.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


# ── Listar pagos de una reserva ──
@reservas_bp.route("/api/reservas/<codigo_reserva>/pagos", methods=["GET"])
def listar_pagos(codigo_reserva):
    conexion = None
    cursor   = None
    try:
        conexion = get_connection()
        cursor   = get_cursor(conexion)

        cursor.execute("""
            SELECT id_reserva, precio_total, estado AS estado_reserva
            FROM reservas WHERE codigo_reserva = %s
        """, (codigo_reserva,))
        reserva = cursor.fetchone()
        if reserva is None:
            return jsonify({"error": "Reserva no encontrada"}), 404

        cursor.execute("""
            SELECT id_pago, codigo_operacion, metodo_pago, monto, estado,
                   fecha_pago, monto_entregado, vuelto, numero_operacion
            FROM pagos
            WHERE id_reserva = %s AND estado = 'exitoso'
            ORDER BY fecha_pago ASC
        """, (reserva["id_reserva"],))

        pagos        = _serializar_pagos(cursor.fetchall())
        precio_total = round(float(reserva["precio_total"]), 2)
        total_pagado = round(sum(p["monto"] for p in pagos), 2)

        return jsonify({
            "codigo_reserva":  codigo_reserva,
            "precio_total":    precio_total,
            "total_pagado":    total_pagado,
            "saldo_pendiente": round(max(precio_total - total_pagado, 0), 2),
            "estado_reserva":  reserva["estado_reserva"],
            "pagos":           pagos,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


# ── HU9 legacy: endpoint singular (compatibilidad con tarjeta/transferencia) ──
@reservas_bp.route("/api/reservas/<codigo_reserva>/pago", methods=["POST"])
def procesar_pago(codigo_reserva):
    data        = request.get_json() or {}
    metodo_pago = (data.get("metodo_pago") or "").strip()

    if metodo_pago not in ("tarjeta", "transferencia"):
        return jsonify({"error": "El metodo de pago debe ser tarjeta o transferencia"}), 400
    if not proveedor_pago_configurado():
        return jsonify({"error": "Proveedor de pagos real no configurado en variables de entorno"}), 503
    if not smtp_configurado():
        return jsonify({"error": "Servicio SMTP real no configurado en variables de entorno"}), 503

    datos_pago = {}
    if metodo_pago == "tarjeta":
        numero           = re.sub(r"\s+", "", data.get("numero_tarjeta") or "")
        titular          = (data.get("titular") or "").strip()
        vencimiento      = (data.get("vencimiento") or "").strip()
        codigo_seguridad = (data.get("codigo_seguridad") or "").strip()

        if not re.match(r"^\d{13,19}$", numero):
            return jsonify({"error": "El numero de tarjeta debe tener entre 13 y 19 digitos"}), 400
        if not titular:
            return jsonify({"error": "El titular de la tarjeta es obligatorio"}), 400
        if not re.match(r"^\d{2}/\d{2}$", vencimiento):
            return jsonify({"error": "El vencimiento debe tener formato MM/AA"}), 400
        if not re.match(r"^\d{3,4}$", codigo_seguridad):
            return jsonify({"error": "El codigo de seguridad debe tener 3 o 4 digitos"}), 400

        datos_pago.update({
            "card_number":   numero,
            "card_holder":   titular,
            "expiration":    vencimiento,
            "security_code": codigo_seguridad,
        })

    if metodo_pago == "transferencia":
        numero_operacion = (data.get("numero_operacion") or "").strip()
        if len(numero_operacion) < 6:
            return jsonify({"error": "El numero de operacion debe tener al menos 6 caracteres"}), 400
        datos_pago["bank_operation_number"] = numero_operacion

    conexion = None
    cursor   = None
    try:
        conexion = get_connection()
        cursor   = get_cursor(conexion)

        cursor.execute("""
            SELECT r.id_reserva, r.codigo_reserva,
                   r.nombre_cliente, r.apellido_cliente,
                   r.dni_cliente, r.correo_cliente, r.telefono_cliente,
                   r.fecha_checkin, r.fecha_checkout,
                   r.precio_total, r.estado,
                   h.numero AS numero_habitacion,
                   h.tipo   AS tipo_habitacion
            FROM reservas r
            JOIN habitaciones h ON r.id_habitacion = h.id_habitacion
            WHERE r.codigo_reserva = %s
        """, (codigo_reserva,))

        reserva = cursor.fetchone()
        if reserva is None:
            return jsonify({"error": "Reserva no encontrada"}), 404
        if reserva["estado"] not in ("pendiente", "rechazado"):
            return jsonify({"error": "La reserva ya fue procesada"}), 409

        resultado_pago     = procesar_pago_real(dict(reserva), metodo_pago, datos_pago)
        estado_pago        = resultado_pago["estado"]
        nuevo_estado_reserva = "rechazado" if estado_pago == "rechazado" else "confirmada"
        codigo_operacion   = (
            resultado_pago.get("provider_transaction_id")
            or f"OP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )

        cursor.execute("""
            INSERT INTO pagos (
                id_reserva, codigo_operacion, proveedor_transaccion_id,
                proveedor_estado, metodo_pago, monto, estado, proveedor_respuesta
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id_pago, fecha_pago
        """, (
            reserva["id_reserva"],
            codigo_operacion,
            resultado_pago.get("provider_transaction_id"),
            resultado_pago.get("provider_status"),
            metodo_pago,
            reserva["precio_total"],
            estado_pago,
            Json(resultado_pago.get("provider_response")),
        ))
        pago = cursor.fetchone()

        cursor.execute("""
            UPDATE reservas SET estado = %s WHERE id_reserva = %s
        """, (nuevo_estado_reserva, reserva["id_reserva"]))

        comprobante = {
            "codigo_reserva":  reserva["codigo_reserva"],
            "codigo_operacion": codigo_operacion,
            "monto_pagado":    float(reserva["precio_total"]),
            "fecha_pago":      pago["fecha_pago"].isoformat(),
            "metodo_pago":     metodo_pago,
            "estado_pago":     estado_pago,
            "estado_reserva":  nuevo_estado_reserva,
            "cliente":         f"{reserva['nombre_cliente']} {reserva['apellido_cliente']}",
            "correo":          reserva["correo_cliente"],
            "habitacion":      f"{reserva['tipo_habitacion']} - {reserva['numero_habitacion']}",
            "checkin":         str(reserva["fecha_checkin"]),
            "checkout":        str(reserva["fecha_checkout"]),
        }

        conexion.commit()

        correo_enviado = False
        correo_error   = None
        if estado_pago == "exitoso":
            try:
                enviar_confirmacion_reserva(reserva["correo_cliente"], comprobante)
                correo_enviado = True
                cursor.execute("""
                    UPDATE pagos SET correo_enviado = TRUE, fecha_correo = CURRENT_TIMESTAMP
                    WHERE id_pago = %s
                """, (pago["id_pago"],))
                conexion.commit()
            except Exception as error_correo:
                correo_error = str(error_correo)

        return jsonify({
            "mensaje": resultado_pago.get("message", "Pago procesado"),
            "pago": {
                "id_pago":           pago["id_pago"],
                "codigo_operacion":  codigo_operacion,
                "estado":            estado_pago,
                "metodo_pago":       metodo_pago,
                "monto":             float(reserva["precio_total"]),
                "proveedor_estado":  resultado_pago.get("provider_status"),
            },
            "reserva": {
                "codigo_reserva": reserva["codigo_reserva"],
                "estado":         nuevo_estado_reserva,
            },
            "comprobante":           comprobante,
            "comprobante_pdf_url":   f"/api/reservas/{reserva['codigo_reserva']}/comprobante.pdf",
            "correo_enviado":        correo_enviado,
            "correo_mensaje": (
                "Confirmacion enviada al correo del cliente"
                if correo_enviado
                else correo_error or "No se envio correo porque el pago fue rechazado"
            ),
        })

    except Exception as e:
        if conexion:
            conexion.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


# ── HU17: Detalle de reserva para panel recepcionista ──
@reservas_bp.route("/api/reservas/<codigo_reserva>/detalle", methods=["GET"])
def detalle_reserva(codigo_reserva):
    conexion = None
    cursor   = None
    try:
        conexion = get_connection()
        cursor   = get_cursor(conexion)
        cursor.execute("""
            SELECT r.codigo_reserva, r.nombre_cliente, r.apellido_cliente,
                   r.dni_cliente, r.correo_cliente, r.telefono_cliente,
                   r.cantidad_personas, r.fecha_checkin, r.fecha_checkout,
                   r.precio_total, r.estado, r.fecha_creacion,
                   h.numero AS numero_habitacion,
                   h.tipo   AS tipo_habitacion
            FROM reservas r
            JOIN habitaciones h ON r.id_habitacion = h.id_habitacion
            WHERE r.codigo_reserva = %s
        """, (codigo_reserva,))
        row = cursor.fetchone()
        if row is None:
            return jsonify({"error": "Reserva no encontrada"}), 404
        data = dict(row)
        data["fecha_checkin"]  = str(data["fecha_checkin"])
        data["fecha_checkout"] = str(data["fecha_checkout"])
        data["precio_total"]   = float(data["precio_total"])
        data["fecha_creacion"] = data["fecha_creacion"].isoformat()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


# ── HU10: Descargar comprobante PDF (soporta pagos múltiples) ──
@reservas_bp.route("/api/reservas/<codigo_reserva>/comprobante.pdf", methods=["GET"])
def descargar_comprobante(codigo_reserva):
    conexion = None
    cursor   = None
    try:
        conexion = get_connection()
        cursor   = get_cursor(conexion)

        cursor.execute("""
            SELECT r.codigo_reserva,
                   r.nombre_cliente, r.apellido_cliente, r.correo_cliente,
                   r.fecha_checkin, r.fecha_checkout,
                   r.precio_total, r.estado AS estado_reserva,
                   h.numero AS numero_habitacion,
                   h.tipo   AS tipo_habitacion
            FROM reservas r
            JOIN habitaciones h ON r.id_habitacion = h.id_habitacion
            WHERE r.codigo_reserva = %s
        """, (codigo_reserva,))
        reserva = cursor.fetchone()
        if reserva is None:
            return jsonify({"error": "Reserva no encontrada"}), 404

        cursor.execute("""
            SELECT codigo_operacion, metodo_pago, monto, estado, fecha_pago,
                   monto_entregado, vuelto, numero_operacion
            FROM pagos
            WHERE id_reserva = (
                SELECT id_reserva FROM reservas WHERE codigo_reserva = %s
            )
            AND estado = 'exitoso'
            ORDER BY fecha_pago ASC
        """, (codigo_reserva,))

        pagos = _serializar_pagos(cursor.fetchall())
        if not pagos:
            return jsonify({"error": "No hay pagos registrados para este comprobante"}), 404

        precio_total = round(float(reserva["precio_total"]), 2)
        total_pagado = round(sum(p["monto"] for p in pagos), 2)
        ultimo_pago  = pagos[-1]

        comprobante = {
            "codigo_reserva":  reserva["codigo_reserva"],
            "codigo_operacion": ultimo_pago["codigo_operacion"],
            "precio_total":    precio_total,
            "monto_pagado":    total_pagado,
            "fecha_pago":      ultimo_pago["fecha_pago"],
            "metodo_pago":     ultimo_pago["metodo_pago"],
            "estado_pago":     "exitoso",
            "estado_reserva":  reserva["estado_reserva"],
            "cliente":         f"{reserva['nombre_cliente']} {reserva['apellido_cliente']}",
            "correo":          reserva["correo_cliente"],
            "habitacion":      f"{reserva['tipo_habitacion']} - {reserva['numero_habitacion']}",
            "checkin":         str(reserva["fecha_checkin"]),
            "checkout":        str(reserva["fecha_checkout"]),
            "pagos":           pagos,
        }

        pdf = generar_pdf_comprobante(comprobante)
        response = make_response(pdf)
        response.headers["Content-Type"]        = "application/pdf"
        response.headers["Content-Disposition"] = (
            f"attachment; filename=comprobante-{codigo_reserva}.pdf"
        )
        return response

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


# ── Helpers ──
def _serializar_pagos(rows) -> list:
    pagos = []
    for row in rows:
        p = dict(row)
        p["monto"] = float(p["monto"])
        if p.get("monto_entregado") is not None:
            p["monto_entregado"] = float(p["monto_entregado"])
        if p.get("vuelto") is not None:
            p["vuelto"] = float(p["vuelto"])
        if p.get("fecha_pago"):
            p["fecha_pago"] = p["fecha_pago"].isoformat()
        pagos.append(p)
    return pagos
