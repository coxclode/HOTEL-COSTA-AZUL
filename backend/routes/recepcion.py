from flask import Blueprint, jsonify, request
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
                r.estado          AS estado_reserva,
                r.precio_total    AS precio_total,
                h.tipo            AS tipo_habitacion,
                h.numero          AS numero_habitacion
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
            if notif.get("precio_total") is not None:
                notif["precio_total"] = float(notif["precio_total"])

        return jsonify({"notificaciones": notificaciones, "cantidad": len(notificaciones)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


# ── Listar todas las reservas (recepción) ──
@recepcion_bp.route("/api/recepcion/reservas", methods=["GET"])
def listar_todas_reservas():
    estado = request.args.get("estado", "").strip()
    q      = request.args.get("q", "").strip().lower()

    conexion = None
    cursor   = None
    try:
        conexion = get_connection()
        cursor   = get_cursor(conexion)

        filtro_estado = "AND r.estado = %s" if estado else ""
        params = [estado] if estado else []

        cursor.execute(f"""
            SELECT r.codigo_reserva, r.nombre_cliente, r.apellido_cliente,
                   r.dni_cliente, r.correo_cliente, r.telefono_cliente,
                   r.cantidad_personas, r.fecha_checkin, r.fecha_checkout,
                   r.precio_total, r.estado, r.fecha_creacion,
                   h.numero AS numero_habitacion, h.tipo AS tipo_habitacion
            FROM reservas r
            JOIN habitaciones h ON r.id_habitacion = h.id_habitacion
            WHERE 1=1 {filtro_estado}
            ORDER BY r.fecha_creacion DESC
            LIMIT 100
        """, params)

        reservas = []
        for row in cursor.fetchall():
            r = dict(row)
            r["precio_total"]   = float(r["precio_total"])
            r["fecha_checkin"]  = str(r["fecha_checkin"])
            r["fecha_checkout"] = str(r["fecha_checkout"])
            r["fecha_creacion"] = r["fecha_creacion"].isoformat()
            reservas.append(r)

        if q:
            reservas = [
                r for r in reservas
                if q in r["codigo_reserva"].lower()
                or q in r["nombre_cliente"].lower()
                or q in r["apellido_cliente"].lower()
                or q in (r["dni_cliente"] or "")
            ]

        return jsonify({"reservas": reservas, "total": len(reservas)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conexion: conexion.close()


# ── Check-in ──
@recepcion_bp.route("/api/recepcion/reservas/<codigo>/checkin", methods=["PATCH"])
def hacer_checkin(codigo):
    conexion = None
    cursor   = None
    try:
        conexion = get_connection()
        cursor   = get_cursor(conexion)

        cursor.execute(
            "SELECT id_reserva, estado FROM reservas WHERE codigo_reserva = %s",
            (codigo,)
        )
        row = cursor.fetchone()
        if row is None:
            return jsonify({"error": "Reserva no encontrada"}), 404
        if row["estado"] != "confirmada":
            return jsonify({"error": f"Solo se puede hacer check-in de reservas confirmadas (estado actual: {row['estado']})"}), 409

        cursor.execute(
            "UPDATE reservas SET estado = 'en_hospedaje' WHERE id_reserva = %s",
            (row["id_reserva"],)
        )
        conexion.commit()
        return jsonify({"mensaje": "Check-in registrado", "estado": "en_hospedaje"})

    except Exception as e:
        if conexion: conexion.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conexion: conexion.close()


# ── Check-out ──
@recepcion_bp.route("/api/recepcion/reservas/<codigo>/checkout", methods=["PATCH"])
def hacer_checkout(codigo):
    conexion = None
    cursor   = None
    try:
        conexion = get_connection()
        cursor   = get_cursor(conexion)

        cursor.execute(
            "SELECT id_reserva, estado FROM reservas WHERE codigo_reserva = %s",
            (codigo,)
        )
        row = cursor.fetchone()
        if row is None:
            return jsonify({"error": "Reserva no encontrada"}), 404
        if row["estado"] != "en_hospedaje":
            return jsonify({"error": f"Solo se puede hacer check-out de huéspedes en hospedaje (estado actual: {row['estado']})"}), 409

        cursor.execute(
            "UPDATE reservas SET estado = 'completada' WHERE id_reserva = %s",
            (row["id_reserva"],)
        )
        conexion.commit()
        return jsonify({"mensaje": "Check-out registrado", "estado": "completada"})

    except Exception as e:
        if conexion: conexion.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conexion: conexion.close()


# ── Cancelar reserva ──
@recepcion_bp.route("/api/recepcion/reservas/<codigo>/cancelar", methods=["PATCH"])
def cancelar_reserva(codigo):
    conexion = None
    cursor   = None
    try:
        conexion = get_connection()
        cursor   = get_cursor(conexion)

        cursor.execute(
            "SELECT id_reserva, estado FROM reservas WHERE codigo_reserva = %s",
            (codigo,)
        )
        row = cursor.fetchone()
        if row is None:
            return jsonify({"error": "Reserva no encontrada"}), 404
        if row["estado"] not in ("pendiente", "confirmada"):
            return jsonify({"error": f"No se puede cancelar una reserva en estado '{row['estado']}'"}), 409

        cursor.execute(
            "UPDATE reservas SET estado = 'cancelada' WHERE id_reserva = %s",
            (row["id_reserva"],)
        )
        conexion.commit()
        return jsonify({"mensaje": "Reserva cancelada", "estado": "cancelada"})

    except Exception as e:
        if conexion: conexion.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conexion: conexion.close()


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
