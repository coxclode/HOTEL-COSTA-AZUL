from flask import Blueprint, request, jsonify
from datetime import datetime
from db import get_connection, get_cursor
from services.reservas_service import (
    generar_codigo_reserva,
    calcular_noches,
    calcular_precio_total,
)

reservas_bp = Blueprint("reservas", __name__)


# ── HU6 / HU7: Crear reserva (Sprint 2 confirmar → Sprint 3 generar) ──
@reservas_bp.route("/api/reservas", methods=["POST"])
def crear_reserva():
    data = request.get_json()

    campos = ["id_habitacion", "nombre", "apellido", "dni", "correo",
              "telefono", "checkin", "checkout"]
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

    conexion = None
    cursor = None
    try:
        conexion = get_connection()
        cursor = get_cursor(conexion)

        # Verificar que la habitación sigue disponible (HU4 criterio de aceptación)
        cursor.execute("""
            SELECT precio_base, estado FROM habitaciones
            WHERE id_habitacion = %s
        """, (data["id_habitacion"],))
        habitacion = cursor.fetchone()

        if habitacion is None:
            return jsonify({"error": "Habitación no encontrada"}), 404
        if habitacion["estado"] != "Disponible":
            return jsonify({"error": "La habitación ya no está disponible"}), 409

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
                 fecha_checkin, fecha_checkout, precio_total, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pendiente')
            RETURNING id_reserva
        """, (
            codigo,
            data["id_habitacion"],
            data["nombre"].strip(),
            data["apellido"].strip(),
            data["dni"].strip(),
            data["correo"].strip(),
            data["telefono"].strip(),
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
