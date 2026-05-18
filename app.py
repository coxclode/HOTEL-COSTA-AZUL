from flask import Flask, render_template, request, redirect, flash, url_for
from db import get_connection

app = Flask(__name__)
app.secret_key = "hotel_costa_azul_dev"


# =========================================================
# RUTA PRINCIPAL
# =========================================================
@app.route("/")
def inicio():
    return render_template("index.html")


# =========================================================
# PROBAR CONEXIÓN A MYSQL
# =========================================================
@app.route("/probar-bd")
def probar_bd():
    conexion = None
    cursor = None

    try:
        conexion = get_connection()
        cursor = conexion.cursor()

        cursor.execute("SELECT COUNT(*) FROM habitaciones")
        fila = cursor.fetchone()

        total_habitaciones = 0

        if fila is not None:
            total_habitaciones = int(fila[0])

        return f"""
        <h1>Conexión exitosa a MySQL</h1>
        <p>Base de datos: hotel_costa_azul</p>
        <p>Total de habitaciones registradas: {total_habitaciones}</p>
        <a href="/admin/habitaciones">Ir al panel administrador</a>
        """

    except Exception as error:
        return f"""
        <h1>Error al conectar con MySQL</h1>
        <p>{error}</p>
        """, 500

    finally:
        if cursor is not None:
            cursor.close()

        if conexion is not None:
            conexion.close()


# =========================================================
# HU15 - LISTAR HABITACIONES EN PANEL ADMINISTRADOR
# =========================================================
@app.route("/admin/habitaciones")
def admin_habitaciones():
    conexion = None
    cursor = None

    try:
        conexion = get_connection()
        cursor = conexion.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                id_habitacion,
                numero,
                tipo,
                precio_base,
                descripcion,
                estado,
                capacidad,
                imagen
            FROM habitaciones
            ORDER BY id_habitacion ASC
        """)

        habitaciones = cursor.fetchall()

        return render_template(
            "admin_habitaciones.html",
            habitaciones=habitaciones
        )

    except Exception as error:
        return f"""
        <h1>Error al cargar habitaciones</h1>
        <p>{error}</p>
        """, 500

    finally:
        if cursor is not None:
            cursor.close()

        if conexion is not None:
            conexion.close()


# =========================================================
# HU15 - MOSTRAR FORMULARIO PARA NUEVA HABITACIÓN
# =========================================================
@app.route("/admin/habitaciones/nueva")
def nueva_habitacion():
    return render_template(
        "form_habitacion.html",
        titulo="Registrar habitación",
        accion=url_for("guardar_habitacion"),
        habitacion=None
    )


# =========================================================
# HU15 - GUARDAR NUEVA HABITACIÓN
# =========================================================
@app.route("/admin/habitaciones/guardar", methods=["POST"])
def guardar_habitacion():
    numero = request.form.get("numero", "").strip()
    tipo = request.form.get("tipo", "").strip()
    precio_base = request.form.get("precio_base", "").strip()
    descripcion = request.form.get("descripcion", "").strip()
    estado = request.form.get("estado", "").strip()
    capacidad = request.form.get("capacidad", "").strip()

    if not numero or not tipo or not precio_base or not descripcion or not estado or not capacidad:
        flash("Todos los campos obligatorios deben estar completos.")
        return redirect(url_for("nueva_habitacion"))

    try:
        precio_base = float(precio_base)
        capacidad = int(capacidad)
    except ValueError:
        flash("El precio y la capacidad deben ser valores numéricos.")
        return redirect(url_for("nueva_habitacion"))

    if precio_base < 0:
        flash("El precio no puede ser negativo.")
        return redirect(url_for("nueva_habitacion"))

    if capacidad <= 0:
        flash("La capacidad debe ser mayor a cero.")
        return redirect(url_for("nueva_habitacion"))

    conexion = None
    cursor = None

    try:
        conexion = get_connection()
        cursor = conexion.cursor()

        cursor.execute("""
            INSERT INTO habitaciones
            (numero, tipo, precio_base, descripcion, estado, capacidad, imagen)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            numero,
            tipo,
            precio_base,
            descripcion,
            estado,
            capacidad,
            None
        ))

        conexion.commit()

        flash("Habitación registrada correctamente.")
        return redirect(url_for("admin_habitaciones"))

    except Exception as error:
        return f"""
        <h1>Error al registrar habitación</h1>
        <p>{error}</p>
        """, 500

    finally:
        if cursor is not None:
            cursor.close()

        if conexion is not None:
            conexion.close()


# =========================================================
# HU15 - MOSTRAR FORMULARIO PARA EDITAR HABITACIÓN
# =========================================================
@app.route("/admin/habitaciones/editar/<int:id_habitacion>")
def editar_habitacion(id_habitacion):
    conexion = None
    cursor = None

    try:
        conexion = get_connection()
        cursor = conexion.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                id_habitacion,
                numero,
                tipo,
                precio_base,
                descripcion,
                estado,
                capacidad,
                imagen
            FROM habitaciones
            WHERE id_habitacion = %s
        """, (id_habitacion,))

        habitacion = cursor.fetchone()

        if habitacion is None:
            return "<h1>Habitación no encontrada</h1>", 404

        return render_template(
            "form_habitacion.html",
            titulo="Editar habitación",
            accion=url_for("actualizar_habitacion", id_habitacion=id_habitacion),
            habitacion=habitacion
        )

    except Exception as error:
        return f"""
        <h1>Error al cargar habitación</h1>
        <p>{error}</p>
        """, 500

    finally:
        if cursor is not None:
            cursor.close()

        if conexion is not None:
            conexion.close()


# =========================================================
# HU15 - ACTUALIZAR HABITACIÓN
# =========================================================
@app.route("/admin/habitaciones/actualizar/<int:id_habitacion>", methods=["POST"])
def actualizar_habitacion(id_habitacion):
    numero = request.form.get("numero", "").strip()
    tipo = request.form.get("tipo", "").strip()
    precio_base = request.form.get("precio_base", "").strip()
    descripcion = request.form.get("descripcion", "").strip()
    estado = request.form.get("estado", "").strip()
    capacidad = request.form.get("capacidad", "").strip()

    if not numero or not tipo or not precio_base or not descripcion or not estado or not capacidad:
        flash("Todos los campos obligatorios deben estar completos.")
        return redirect(url_for("editar_habitacion", id_habitacion=id_habitacion))

    try:
        precio_base = float(precio_base)
        capacidad = int(capacidad)
    except ValueError:
        flash("El precio y la capacidad deben ser valores numéricos.")
        return redirect(url_for("editar_habitacion", id_habitacion=id_habitacion))

    if precio_base < 0:
        flash("El precio no puede ser negativo.")
        return redirect(url_for("editar_habitacion", id_habitacion=id_habitacion))

    if capacidad <= 0:
        flash("La capacidad debe ser mayor a cero.")
        return redirect(url_for("editar_habitacion", id_habitacion=id_habitacion))

    conexion = None
    cursor = None

    try:
        conexion = get_connection()
        cursor = conexion.cursor()

        cursor.execute("""
            UPDATE habitaciones
            SET
                numero = %s,
                tipo = %s,
                precio_base = %s,
                descripcion = %s,
                estado = %s,
                capacidad = %s
            WHERE id_habitacion = %s
        """, (
            numero,
            tipo,
            precio_base,
            descripcion,
            estado,
            capacidad,
            id_habitacion
        ))

        conexion.commit()

        flash("Habitación actualizada correctamente.")
        return redirect(url_for("admin_habitaciones"))

    except Exception as error:
        return f"""
        <h1>Error al actualizar habitación</h1>
        <p>{error}</p>
        """, 500

    finally:
        if cursor is not None:
            cursor.close()

        if conexion is not None:
            conexion.close()


# =========================================================
# HU18 - CAMBIAR DISPONIBILIDAD DE HABITACIÓN
# Disponible -> Bloqueada
# Bloqueada o Mantenimiento -> Disponible
# =========================================================
@app.route("/admin/habitaciones/cambiar-estado/<int:id_habitacion>", methods=["POST"])
def cambiar_estado_habitacion(id_habitacion):
    conexion = None
    cursor = None

    try:
        conexion = get_connection()
        cursor = conexion.cursor(dictionary=True)

        cursor.execute("""
            SELECT estado
            FROM habitaciones
            WHERE id_habitacion = %s
        """, (id_habitacion,))

        habitacion = cursor.fetchone()

        if habitacion is None:
            return "<h1>Habitación no encontrada</h1>", 404

        estado_actual = habitacion["estado"]

        if estado_actual == "Disponible":
            nuevo_estado = "Bloqueada"
        else:
            nuevo_estado = "Disponible"

        cursor.execute("""
            UPDATE habitaciones
            SET estado = %s
            WHERE id_habitacion = %s
        """, (
            nuevo_estado,
            id_habitacion
        ))

        conexion.commit()

        flash("Estado de habitación actualizado correctamente.")
        return redirect(url_for("admin_habitaciones"))

    except Exception as error:
        return f"""
        <h1>Error al cambiar estado</h1>
        <p>{error}</p>
        """, 500

    finally:
        if cursor is not None:
            cursor.close()

        if conexion is not None:
            conexion.close()


# =========================================================
# VISTA CLIENTE - SOLO HABITACIONES DISPONIBLES
# Esto ayuda a cumplir HU18:
# las habitaciones bloqueadas no deben mostrarse al cliente.
# =========================================================
@app.route("/habitaciones")
def habitaciones_cliente():
    conexion = None
    cursor = None

    try:
        conexion = get_connection()
        cursor = conexion.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                id_habitacion,
                numero,
                tipo,
                precio_base,
                descripcion,
                estado,
                capacidad,
                imagen
            FROM habitaciones
            WHERE estado = 'Disponible'
            ORDER BY id_habitacion ASC
        """)

        habitaciones = cursor.fetchall()

        return render_template(
            "habitaciones_cliente.html",
            habitaciones=habitaciones
        )

    except Exception as error:
        return f"""
        <h1>Error al cargar habitaciones disponibles</h1>
        <p>{error}</p>
        """, 500

    finally:
        if cursor is not None:
            cursor.close()

        if conexion is not None:
            conexion.close()


if __name__ == "__main__":
    app.run(debug=True)