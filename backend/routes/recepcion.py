from flask import Blueprint, jsonify
from db import get_connection, get_cursor

recepcion_bp = Blueprint("recepcion", __name__)


# ── HU17: Polling de notificaciones no leídas ──
@recepcion_bp.route("/api/recepcion/notificaciones", methods=["GET"])
def poll_notificaciones():
    conexion = None
    cursor = None
    try:
        conexion = get_connection()
        cursor = get_cursor(conexion)

        cursor.execute("""
            SELECT
                n.id_notificacion,
                n.tipo,
                n.leido,
                n.fecha_creacion,
                r.codigo_reserva,
                r.nombre_cliente,
                r.apellido_cliente,
                r.fecha_checkin,
                r.fecha_checkout,
                h.tipo  AS tipo_habitacion,
                h.numero AS numero_habitacion
            FROM notificaciones n
            JOIN reservas    r ON n.id_reserva    = r.id_reserva
            JOIN habitaciones h ON r.id_habitacion = h.id_habitacion
            WHERE n.leido = FALSE
            ORDER BY n.fecha_creacion DESC
            LIMIT 20
        """)

        notificaciones = [dict(row) for row in cursor.fetchall()]
        for notif in notificaciones:
            if notif.get("fecha_creacion"):
                notif["fecha_creacion"] = notif["fecha_creacion"].isoformat()
            if notif.get("fecha_checkin"):
                notif["fecha_checkin"] = str(notif["fecha_checkin"])
            if notif.get("fecha_checkout"):
                notif["fecha_checkout"] = str(notif["fecha_checkout"])

        return jsonify({"notificaciones": notificaciones, "cantidad": len(notificaciones)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


# ── HU17: Marcar notificación como leída ──
@recepcion_bp.route("/api/recepcion/notificaciones/<int:id_notificacion>/leer", methods=["PATCH"])
def marcar_leida(id_notificacion):
    conexion = None
    cursor = None
    try:
        conexion = get_connection()
        cursor = get_cursor(conexion)

        cursor.execute("""
            UPDATE notificaciones SET leido = TRUE
            WHERE id_notificacion = %s
        """, (id_notificacion,))

        conexion.commit()
        return jsonify({"mensaje": "Notificación marcada como leída"})

    except Exception as e:
        if conexion:
            conexion.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()
