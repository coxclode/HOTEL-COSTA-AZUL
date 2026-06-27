from flask import Blueprint, request, jsonify, make_response
from datetime import datetime
import re, os
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


# ── HU5: Verificar DNI contra RENIEC (apis.net.pe) ──
@reservas_bp.route("/api/dni/<dni>", methods=["GET"])
def consultar_dni(dni):
    if not re.match(r'^\d{8}$', dni):
        return jsonify({"error": "El DNI debe tener exactamente 8 dígitos"}), 400

    token = os.getenv("APIS_NET_PE_TOKEN", "")
    reniec_url = os.getenv("APIS_NET_PE_RENIEC_URL", "https://api.apis.net.pe/v2/reniec/dni")
    if not token:
        return jsonify({
            "error": "Servicio de verificacion DNI no configurado",
            "detalle": "Configura APIS_NET_PE_TOKEN en backend/.env",
        }), 503

    try:
        resp = http_requests.get(
            reniec_url,
            params={"numero": dni},
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            nombres = data.get("nombres") or data.get("nombresCompletos") or ""
            apellido_paterno = data.get("apellidoPaterno") or data.get("apellido_paterno") or ""
            apellido_materno = data.get("apellidoMaterno") or data.get("apellido_materno") or ""

            if not nombres and not apellido_paterno and not apellido_materno:
                return jsonify({
                    "error": "RENIEC no devolvio datos personales para el DNI consultado"
                }), 502

            return jsonify({
                "dni": dni,
                "nombres": nombres,
                "apellido_paterno": apellido_paterno,
                "apellido_materno": apellido_materno,
                "nombre_completo": " ".join(
                    parte for parte in [nombres, apellido_paterno, apellido_materno] if parte
                ),
                "verificado": True,
            })
        elif resp.status_code == 404:
            return jsonify({"error": "DNI no encontrado en RENIEC"}), 404
        elif resp.status_code in (401, 403):
            return jsonify({
                "error": "Credenciales RENIEC invalidas o sin permisos",
                "detalle": "Verifica APIS_NET_PE_TOKEN",
            }), 502
        else:
            return jsonify({
                "error": "Error al consultar RENIEC",
                "estado_proveedor": resp.status_code,
            }), 502
    except http_requests.exceptions.Timeout:
        return jsonify({"error": "Tiempo de espera agotado al consultar RENIEC"}), 504
    except http_requests.exceptions.RequestException:
        return jsonify({"error": "Error de conexión con RENIEC"}), 500


# ── HU6 / HU7: Crear reserva (Sprint 2 confirmar → Sprint 3 generar) ──
@reservas_bp.route("/api/reservas", methods=["POST"])
def crear_reserva():
    data = request.get_json()

    campos = ["id_habitacion", "nombre", "apellido", "dni", "correo",
              "telefono", "checkin", "checkout", "personas"]
    for campo in campos:
        if not data.get(campo):
            return jsonify({"error": f"El campo '{campo}' es obligatorio"}), 400

    try:
        fecha_checkin = datetime.strptime(data["checkin"], "%Y-%m-%d").date()
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
    cursor = None
    try:
        conexion = get_connection()
        cursor = get_cursor(conexion)

        # Verificar que la habitación sigue disponible (HU4 criterio de aceptación)
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

        # Verificar que no haya solapamiento de fechas
        cursor.execute("""
            SELECT COUNT(*) AS total FROM reservas
            WHERE id_habitacion = %s
            AND estado IN ('pendiente', 'confirmada', 'en_hospedaje')
            AND fecha_checkin  < %s
            AND fecha_checkout > %s
        """, (data["id_habitacion"], fecha_checkout, fecha_checkin))

        if cursor.fetchone()["total"] > 0:
            return jsonify({"error": "La habitación no está disponible en esas fechas"}), 409

        noches = calcular_noches(fecha_checkin, fecha_checkout)
        precio_total = calcular_precio_total(float(habitacion["precio_base"]), noches)
        codigo = generar_codigo_reserva()

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

        # Insertar notificación para recepcionista (HU17)
        cursor.execute("""
            INSERT INTO notificaciones (id_reserva, tipo, leido)
            VALUES (%s, 'nueva_reserva', FALSE)
        """, (id_reserva,))

        conexion.commit()

        return jsonify({
            "mensaje": "Reserva creada exitosamente",
            "codigo_reserva": codigo,
            "precio_total": precio_total,
            "noches": noches,
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


# ── HU9 / HU10: Procesar pago real por API externa y generar comprobante ──
@reservas_bp.route("/api/reservas/<codigo_reserva>/pago", methods=["POST"])
def procesar_pago(codigo_reserva):
    data = request.get_json() or {}
    metodo_pago = (data.get("metodo_pago") or "").strip()

    if metodo_pago not in ("tarjeta", "transferencia"):
        return jsonify({"error": "El metodo de pago debe ser tarjeta o transferencia"}), 400
    if not proveedor_pago_configurado():
        return jsonify({"error": "Proveedor de pagos real no configurado en variables de entorno"}), 503
    if not smtp_configurado():
        return jsonify({"error": "Servicio SMTP real no configurado en variables de entorno"}), 503

    datos_pago = {}
    if metodo_pago == "tarjeta":
        numero = re.sub(r"\s+", "", data.get("numero_tarjeta") or "")
        titular = (data.get("titular") or "").strip()
        vencimiento = (data.get("vencimiento") or "").strip()
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
            "card_number": numero,
            "card_holder": titular,
            "expiration": vencimiento,
            "security_code": codigo_seguridad,
        })

    if metodo_pago == "transferencia":
        numero_operacion = (data.get("numero_operacion") or "").strip()
        if len(numero_operacion) < 6:
            return jsonify({"error": "El numero de operacion debe tener al menos 6 caracteres"}), 400
        datos_pago["bank_operation_number"] = numero_operacion

    conexion = None
    cursor = None
    try:
        conexion = get_connection()
        cursor = get_cursor(conexion)

        cursor.execute("""
            SELECT
                r.id_reserva,
                r.codigo_reserva,
                r.nombre_cliente,
                r.apellido_cliente,
                r.dni_cliente,
                r.correo_cliente,
                r.telefono_cliente,
                r.fecha_checkin,
                r.fecha_checkout,
                r.precio_total,
                r.estado,
                h.numero AS numero_habitacion,
                h.tipo AS tipo_habitacion
            FROM reservas r
            JOIN habitaciones h ON r.id_habitacion = h.id_habitacion
            WHERE r.codigo_reserva = %s
        """, (codigo_reserva,))

        reserva = cursor.fetchone()
        if reserva is None:
            return jsonify({"error": "Reserva no encontrada"}), 404
        if reserva["estado"] not in ("pendiente", "rechazado"):
            return jsonify({"error": "La reserva ya fue procesada"}), 409

        resultado_pago = procesar_pago_real(dict(reserva), metodo_pago, datos_pago)
        estado_pago = resultado_pago["estado"]
        nuevo_estado_reserva = "rechazado" if estado_pago == "rechazado" else "confirmada"
        codigo_operacion = (
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
            UPDATE reservas
            SET estado = %s
            WHERE id_reserva = %s
        """, (nuevo_estado_reserva, reserva["id_reserva"]))

        comprobante = {
            "codigo_reserva": reserva["codigo_reserva"],
            "codigo_operacion": codigo_operacion,
            "monto_pagado": float(reserva["precio_total"]),
            "fecha_pago": pago["fecha_pago"].isoformat(),
            "metodo_pago": metodo_pago,
            "estado_pago": estado_pago,
            "estado_reserva": nuevo_estado_reserva,
            "cliente": f"{reserva['nombre_cliente']} {reserva['apellido_cliente']}",
            "correo": reserva["correo_cliente"],
            "habitacion": f"{reserva['tipo_habitacion']} - {reserva['numero_habitacion']}",
            "checkin": str(reserva["fecha_checkin"]),
            "checkout": str(reserva["fecha_checkout"]),
        }

        conexion.commit()

        correo_enviado = False
        correo_error = None
        if estado_pago == "exitoso":
            try:
                enviar_confirmacion_reserva(reserva["correo_cliente"], comprobante)
                correo_enviado = True
                cursor.execute("""
                    UPDATE pagos
                    SET correo_enviado = TRUE, fecha_correo = CURRENT_TIMESTAMP
                    WHERE id_pago = %s
                """, (pago["id_pago"],))
                conexion.commit()
            except Exception as error_correo:
                correo_error = str(error_correo)

        return jsonify({
            "mensaje": resultado_pago.get("message", "Pago procesado"),
            "pago": {
                "id_pago": pago["id_pago"],
                "codigo_operacion": codigo_operacion,
                "estado": estado_pago,
                "metodo_pago": metodo_pago,
                "monto": float(reserva["precio_total"]),
                "proveedor_estado": resultado_pago.get("provider_status"),
            },
            "reserva": {
                "codigo_reserva": reserva["codigo_reserva"],
                "estado": nuevo_estado_reserva,
            },
            "comprobante": comprobante,
            "comprobante_pdf_url": f"/api/reservas/{reserva['codigo_reserva']}/comprobante.pdf",
            "correo_enviado": correo_enviado,
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
    cursor = None
    try:
        conexion = get_connection()
        cursor = get_cursor(conexion)
        cursor.execute("""
            SELECT
                r.codigo_reserva,
                r.nombre_cliente,
                r.apellido_cliente,
                r.dni_cliente,
                r.correo_cliente,
                r.telefono_cliente,
                r.cantidad_personas,
                r.fecha_checkin,
                r.fecha_checkout,
                r.precio_total,
                r.estado,
                r.fecha_creacion,
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
        data["fecha_checkin"]   = str(data["fecha_checkin"])
        data["fecha_checkout"]  = str(data["fecha_checkout"])
        data["precio_total"]    = float(data["precio_total"])
        data["fecha_creacion"]  = data["fecha_creacion"].isoformat()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


@reservas_bp.route("/api/reservas/<codigo_reserva>/comprobante.pdf", methods=["GET"])
def descargar_comprobante(codigo_reserva):
    conexion = None
    cursor = None
    try:
        conexion = get_connection()
        cursor = get_cursor(conexion)

        cursor.execute("""
            SELECT
                r.codigo_reserva,
                r.nombre_cliente,
                r.apellido_cliente,
                r.correo_cliente,
                r.fecha_checkin,
                r.fecha_checkout,
                r.estado AS estado_reserva,
                h.numero AS numero_habitacion,
                h.tipo AS tipo_habitacion,
                p.codigo_operacion,
                p.metodo_pago,
                p.monto,
                p.estado AS estado_pago,
                p.fecha_pago
            FROM reservas r
            JOIN habitaciones h ON r.id_habitacion = h.id_habitacion
            JOIN pagos p ON r.id_reserva = p.id_reserva
            WHERE r.codigo_reserva = %s
            ORDER BY p.fecha_pago DESC
            LIMIT 1
        """, (codigo_reserva,))

        row = cursor.fetchone()
        if row is None:
            return jsonify({"error": "Comprobante no encontrado"}), 404

        comprobante = {
            "codigo_reserva": row["codigo_reserva"],
            "codigo_operacion": row["codigo_operacion"],
            "monto_pagado": float(row["monto"]),
            "fecha_pago": row["fecha_pago"].isoformat(),
            "metodo_pago": row["metodo_pago"],
            "estado_pago": row["estado_pago"],
            "estado_reserva": row["estado_reserva"],
            "cliente": f"{row['nombre_cliente']} {row['apellido_cliente']}",
            "correo": row["correo_cliente"],
            "habitacion": f"{row['tipo_habitacion']} - {row['numero_habitacion']}",
            "checkin": str(row["fecha_checkin"]),
            "checkout": str(row["fecha_checkout"]),
        }
        pdf = generar_pdf_comprobante(comprobante)
        response = make_response(pdf)
        response.headers["Content-Type"] = "application/pdf"
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
