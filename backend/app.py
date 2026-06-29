import sys
import os
import logging
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, g
from flask_cors import CORS
from dotenv import load_dotenv

from routes.habitaciones import habitaciones_bp
from routes.reservas import reservas_bp
from routes.recepcion import recepcion_bp

load_dotenv(Path(__file__).with_name(".env"), override=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("hotel_costa_azul")

app = Flask(__name__)
CORS(app)


@app.before_request
def _log_request():
    logger.info("→ %s %s", request.method, request.path)


@app.after_request
def _log_response(response):
    logger.info("← %s %s %s", request.method, request.path, response.status_code)
    return response

app.register_blueprint(habitaciones_bp)
app.register_blueprint(reservas_bp)
app.register_blueprint(recepcion_bp)


@app.route("/api/ping")
def ping():
    return {"status": "ok", "proyecto": "Hotel Costa Azul"}


if __name__ == "__main__":
    app.run(debug=True, port=5002)
