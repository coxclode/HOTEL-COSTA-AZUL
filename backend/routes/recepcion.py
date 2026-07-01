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


# ── Modificar reserva (solo con 24h de anticipación) ──
@recepcion_bp.route("/api/recepcion/reservas/<codigo>/modificar", methods=["PATCH"])
def modificar_reserva(codigo):
    from datetime import datetime, timedelta, date as date_type
    data = request.get_json() or {}

    conexion = None
    cursor   = None
    try:
        conexion = get_connection()
        cursor   = get_cursor(conexion)

        cursor.execute("""
            SELECT r.id_reserva, r.estado, r.fecha_checkin, r.id_habitacion,
                   r.nombre_cliente, r.apellido_cliente, r.correo_cliente,
                   r.telefono_cliente, r.cantidad_personas,
                   r.fecha_checkout, h.precio_base
            FROM reservas r
            JOIN habitaciones h ON r.id_habitacion = h.id_habitacion
            WHERE r.codigo_reserva = %s
        """, (codigo,))
        res = cursor.fetchone()

        if res is None:
            return jsonify({"error": "Reserva no encontrada"}), 404

        if res["estado"] not in ("pendiente", "confirmada"):
            return jsonify({"error": f"No se puede modificar una reserva en estado '{res['estado']}'"}), 409

        limite = datetime.now() + timedelta(hours=24)
        checkin_actual = datetime.combine(res["fecha_checkin"], datetime.min.time())
        if checkin_actual <= limite:
            horas_restantes = max(0, int((checkin_actual - datetime.now()).total_seconds() / 3600))
            return jsonify({
                "error": f"No se puede modificar con menos de 24 horas de anticipación. El check-in es en {horas_restantes} hora(s)."
            }), 409

        nueva_checkin  = data.get("nueva_checkin")
        nueva_checkout = data.get("nueva_checkout")
        personas       = data.get("personas")
        nombre         = data.get("nombre", "").strip() or None
        apellido       = data.get("apellido", "").strip() or None
        correo         = data.get("correo", "").strip() or None
        telefono       = data.get("telefono", "").strip() or None

        fecha_checkin  = res["fecha_checkin"]
        fecha_checkout = res["fecha_checkout"]
        precio_base    = float(res["precio_base"])
        recalcular     = False

        if nueva_checkin or nueva_checkout:
            try:
                fecha_checkin  = datetime.strptime(nueva_checkin  or str(res["fecha_checkin"]),  "%Y-%m-%d").date()
                fecha_checkout = datetime.strptime(nueva_checkout or str(res["fecha_checkout"]), "%Y-%m-%d").date()
            except ValueError:
                return jsonify({"error": "Formato de fecha inválido. Use YYYY-MM-DD"}), 400

            if fecha_checkout <= fecha_checkin:
                return jsonify({"error": "El check-out debe ser posterior al check-in"}), 400

            nuevo_ci = datetime.combine(fecha_checkin, datetime.min.time())
            if nuevo_ci <= limite:
                return jsonify({"error": "Las nuevas fechas también deben tener al menos 24 horas de anticipación"}), 409

            cursor.execute("""
                SELECT COUNT(*) AS total FROM reservas
                WHERE id_habitacion = %s
                  AND id_reserva   != %s
                  AND estado IN ('pendiente', 'confirmada', 'en_hospedaje')
                  AND fecha_checkin  < %s
                  AND fecha_checkout > %s
            """, (res["id_habitacion"], res["id_reserva"], fecha_checkout, fecha_checkin))

            if cursor.fetchone()["total"] > 0:
                return jsonify({"error": "La habitación no está disponible en las nuevas fechas"}), 409
            recalcular = True

        if personas is not None:
            try:
                personas = int(personas)
                if personas <= 0:
                    return jsonify({"error": "La cantidad de personas debe ser mayor a cero"}), 400
            except (ValueError, TypeError):
                return jsonify({"error": "personas debe ser numérico"}), 400
        else:
            personas = res["cantidad_personas"]

        from services.reservas_service import calcular_noches, calcular_precio_total
        noches       = calcular_noches(fecha_checkin, fecha_checkout)
        precio_total = calcular_precio_total(precio_base, noches) if recalcular else None

        sets = [
            "fecha_checkin = %s", "fecha_checkout = %s", "cantidad_personas = %s",
            "nombre_cliente = %s", "apellido_cliente = %s",
            "correo_cliente = %s", "telefono_cliente = %s",
        ]
        vals = [
            fecha_checkin, fecha_checkout, personas,
            nombre    or res["nombre_cliente"],
            apellido  or res["apellido_cliente"],
            correo    or res["correo_cliente"],
            telefono  or res["telefono_cliente"],
        ]
        if precio_total is not None:
            sets.append("precio_total = %s")
            vals.append(precio_total)

        vals.append(res["id_reserva"])
        cursor.execute(f"UPDATE reservas SET {', '.join(sets)} WHERE id_reserva = %s", vals)
        conexion.commit()

        return jsonify({
            "mensaje":        "Reserva modificada correctamente",
            "codigo_reserva": codigo,
            "fecha_checkin":  str(fecha_checkin),
            "fecha_checkout": str(fecha_checkout),
            "noches":         noches,
            "precio_total":   precio_total or float(
                cursor.execute("SELECT precio_total FROM reservas WHERE id_reserva=%s", (res["id_reserva"],)) or 0
            ),
        })

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
