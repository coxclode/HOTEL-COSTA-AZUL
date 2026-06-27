from flask import Blueprint, request, jsonify
from datetime import datetime
from db import get_connection, get_cursor

habitaciones_bp = Blueprint("habitaciones", __name__)


# ── HU1 / HU3: Catálogo público de habitaciones disponibles ──
@habitaciones_bp.route("/api/habitaciones", methods=["GET"])
def catalogo_habitaciones():
    conexion = None
    cursor = None
    try:
        conexion = get_connection()
        cursor = get_cursor(conexion)

        cursor.execute("""
            SELECT id_habitacion, numero, tipo, precio_base,
                   descripcion, estado, capacidad, imagen
            FROM habitaciones
            WHERE estado = 'Disponible'
            ORDER BY
                CASE tipo
                    WHEN 'Simple' THEN 1
                    WHEN 'Doble' THEN 2
                    WHEN 'Suite' THEN 3
                    ELSE 4
                END,
                precio_base ASC
        """)

        habitaciones = [dict(row) for row in cursor.fetchall()]
        for h in habitaciones:
            h["precio_base"] = float(h["precio_base"])

        return jsonify({"habitaciones": habitaciones, "total": len(habitaciones)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


# ── HU2: Buscar habitaciones disponibles con filtros de fecha y tipo ──
@habitaciones_bp.route("/api/habitaciones/disponibles", methods=["GET"])
def buscar_disponibles():
    checkin = request.args.get("checkin")
    checkout = request.args.get("checkout")
    tipo = request.args.get("tipo")
    personas = request.args.get("personas", "1")

    if not checkin or not checkout:
        return jsonify({"error": "checkin y checkout son obligatorios"}), 400

    try:
        fecha_checkin = datetime.strptime(checkin, "%Y-%m-%d").date()
        fecha_checkout = datetime.strptime(checkout, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Formato de fecha inválido. Use YYYY-MM-DD"}), 400

    if fecha_checkout <= fecha_checkin:
        return jsonify({"error": "La fecha de salida debe ser posterior a la de entrada"}), 400

    try:
        cantidad_personas = int(personas)
    except (ValueError, TypeError):
        return jsonify({"error": "La cantidad de personas debe ser numerica"}), 400

    if cantidad_personas <= 0:
        return jsonify({"error": "La cantidad de personas debe ser mayor a cero"}), 400

    conexion = None
    cursor = None
    try:
        conexion = get_connection()
        cursor = get_cursor(conexion)

        params = []

        tipo_filter = ""
        if tipo and tipo in ("Simple", "Doble", "Suite"):
            tipo_filter = "AND h.tipo = %s"
            params.append(tipo)

        capacidad_filter = " AND h.capacidad >= %s"
        params.append(cantidad_personas)

        # Descarta habitaciones Bloqueadas y las que ya tienen reserva que se solapa
        cursor.execute(f"""
            SELECT h.id_habitacion, h.numero, h.tipo, h.precio_base,
                   h.descripcion, h.capacidad, h.imagen, h.estado
            FROM habitaciones h
            WHERE h.estado = 'Disponible'
            {tipo_filter}
            {capacidad_filter}
            AND h.id_habitacion NOT IN (
                SELECT r.id_habitacion FROM reservas r
                WHERE r.estado IN ('pendiente', 'confirmada', 'en_hospedaje')
                AND r.fecha_checkin  < %s
                AND r.fecha_checkout > %s
            )
            ORDER BY h.precio_base ASC
        """, params + [fecha_checkout, fecha_checkin])

        habitaciones = [dict(row) for row in cursor.fetchall()]
        for h in habitaciones:
            if h.get("precio_base"):
                h["precio_base"] = float(h["precio_base"])

        return jsonify({"habitaciones": habitaciones, "total": len(habitaciones)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


# ── HU3: Ver detalle de una habitación ──
@habitaciones_bp.route("/api/habitaciones/<int:id_habitacion>", methods=["GET"])
def detalle_habitacion(id_habitacion):
    conexion = None
    cursor = None
    try:
        conexion = get_connection()
        cursor = get_cursor(conexion)

        cursor.execute("""
            SELECT id_habitacion, numero, tipo, precio_base,
                   descripcion, estado, capacidad, imagen
            FROM habitaciones
            WHERE id_habitacion = %s
        """, (id_habitacion,))

        row = cursor.fetchone()
        if row is None:
            return jsonify({"error": "Habitación no encontrada"}), 404

        habitacion = dict(row)
        habitacion["precio_base"] = float(habitacion["precio_base"])
        return jsonify(habitacion)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


# ── HU15: Listar todas las habitaciones (panel admin) ──
@habitaciones_bp.route("/api/admin/habitaciones", methods=["GET"])
def admin_listar():
    conexion = None
    cursor = None
    try:
        conexion = get_connection()
        cursor = get_cursor(conexion)

        cursor.execute("""
            SELECT id_habitacion, numero, tipo, precio_base,
                   descripcion, estado, capacidad, imagen
            FROM habitaciones
            ORDER BY id_habitacion ASC
        """)

        habitaciones = [dict(row) for row in cursor.fetchall()]
        for h in habitaciones:
            h["precio_base"] = float(h["precio_base"])

        return jsonify({"habitaciones": habitaciones})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


# ── HU15: Registrar nueva habitación ──
@habitaciones_bp.route("/api/admin/habitaciones", methods=["POST"])
def admin_crear():
    data = request.get_json()
    numero = (data.get("numero") or "").strip()
    tipo = (data.get("tipo") or "").strip()
    descripcion = (data.get("descripcion") or "").strip()
    estado = (data.get("estado") or "Disponible").strip()

    if not numero or not tipo or not descripcion:
        return jsonify({"error": "numero, tipo y descripcion son obligatorios"}), 400

    try:
        precio_base = float(data.get("precio_base", 0))
        capacidad = int(data.get("capacidad", 1))
    except (ValueError, TypeError):
        return jsonify({"error": "precio_base y capacidad deben ser numéricos"}), 400

    if precio_base < 0:
        return jsonify({"error": "El precio no puede ser negativo"}), 400
    if capacidad <= 0:
        return jsonify({"error": "La capacidad debe ser mayor a cero"}), 400

    conexion = None
    cursor = None
    try:
        conexion = get_connection()
        cursor = get_cursor(conexion)

        cursor.execute("""
            INSERT INTO habitaciones (numero, tipo, precio_base, descripcion, estado, capacidad)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id_habitacion
        """, (numero, tipo, precio_base, descripcion, estado, capacidad))

        nuevo_id = cursor.fetchone()["id_habitacion"]
        conexion.commit()

        return jsonify({"mensaje": "Habitación registrada", "id_habitacion": nuevo_id}), 201

    except Exception as e:
        if conexion:
            conexion.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


# ── HU15: Editar habitación ──
@habitaciones_bp.route("/api/admin/habitaciones/<int:id_habitacion>", methods=["PUT"])
def admin_editar(id_habitacion):
    data = request.get_json()
    numero = (data.get("numero") or "").strip()
    tipo = (data.get("tipo") or "").strip()
    descripcion = (data.get("descripcion") or "").strip()
    estado = (data.get("estado") or "").strip()

    if not numero or not tipo or not descripcion or not estado:
        return jsonify({"error": "Todos los campos son obligatorios"}), 400

    try:
        precio_base = float(data.get("precio_base", 0))
        capacidad = int(data.get("capacidad", 1))
    except (ValueError, TypeError):
        return jsonify({"error": "precio_base y capacidad deben ser numéricos"}), 400

    if precio_base < 0:
        return jsonify({"error": "El precio no puede ser negativo"}), 400

    conexion = None
    cursor = None
    try:
        conexion = get_connection()
        cursor = get_cursor(conexion)

        cursor.execute("""
            UPDATE habitaciones
            SET numero=%s, tipo=%s, precio_base=%s, descripcion=%s,
                estado=%s, capacidad=%s,
                fecha_actualizacion=CURRENT_TIMESTAMP
            WHERE id_habitacion=%s
        """, (numero, tipo, precio_base, descripcion, estado, capacidad, id_habitacion))

        if cursor.rowcount == 0:
            return jsonify({"error": "Habitación no encontrada"}), 404

        conexion.commit()
        return jsonify({"mensaje": "Habitación actualizada"})

    except Exception as e:
        if conexion:
            conexion.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


# ── HU15: Eliminar habitación ──
@habitaciones_bp.route("/api/admin/habitaciones/<int:id_habitacion>", methods=["DELETE"])
def admin_eliminar(id_habitacion):
    conexion = None
    cursor = None
    try:
        conexion = get_connection()
        cursor = get_cursor(conexion)

        cursor.execute(
            "DELETE FROM habitaciones WHERE id_habitacion = %s",
            (id_habitacion,)
        )

        if cursor.rowcount == 0:
            return jsonify({"error": "Habitación no encontrada"}), 404

        conexion.commit()
        return jsonify({"mensaje": "Habitación eliminada"})

    except Exception as e:
        if conexion:
            conexion.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


# ── HU18: Cambiar disponibilidad (toggle Disponible ↔ Bloqueada) ──
@habitaciones_bp.route("/api/admin/habitaciones/<int:id_habitacion>/disponibilidad", methods=["PATCH"])
def admin_toggle_disponibilidad(id_habitacion):
    conexion = None
    cursor = None
    try:
        conexion = get_connection()
        cursor = get_cursor(conexion)

        cursor.execute(
            "SELECT estado FROM habitaciones WHERE id_habitacion = %s",
            (id_habitacion,)
        )
        row = cursor.fetchone()
        if row is None:
            return jsonify({"error": "Habitación no encontrada"}), 404

        nuevo_estado = "Bloqueada" if row["estado"] == "Disponible" else "Disponible"

        cursor.execute("""
            UPDATE habitaciones
            SET estado = %s, fecha_actualizacion = CURRENT_TIMESTAMP
            WHERE id_habitacion = %s
        """, (nuevo_estado, id_habitacion))

        conexion.commit()
        return jsonify({"mensaje": f"Estado cambiado a {nuevo_estado}", "nuevo_estado": nuevo_estado})

    except Exception as e:
        if conexion:
            conexion.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()
