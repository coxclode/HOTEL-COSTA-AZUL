from flask import Flask, render_template
from db import get_connection

app = Flask(__name__)


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/probar-bd")
def probar_bd():
    conexion = None
    cursor = None

    try:
        conexion = get_connection()
        cursor = conexion.cursor()

        consulta = "SELECT COUNT(*) FROM habitaciones"
        cursor.execute(consulta)

        fila = cursor.fetchone()

        total_habitaciones = 0

        if fila is not None:
            total_habitaciones = int(fila[0])  # type: ignore[index]

        return f"""
        <h1>Conexión exitosa a MySQL</h1>
        <p>Base de datos: hotel_costa_azul</p>
        <p>Total de habitaciones registradas: {total_habitaciones}</p>
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


if __name__ == "__main__":
    app.run(debug=True)