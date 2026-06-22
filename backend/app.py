import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

from routes.habitaciones import habitaciones_bp
from routes.reservas import reservas_bp
from routes.recepcion import recepcion_bp

load_dotenv()

app = Flask(__name__)
CORS(app)

app.register_blueprint(habitaciones_bp)
app.register_blueprint(reservas_bp)
app.register_blueprint(recepcion_bp)


@app.route("/api/ping")
def ping():
    return {"status": "ok", "proyecto": "Hotel Costa Azul"}


if __name__ == "__main__":
    app.run(debug=True, port=5000)
