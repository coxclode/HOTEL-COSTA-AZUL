import os
import psycopg2
import psycopg2.extras
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"), override=True)
if not os.getenv("DATABASE_URL") and os.getenv("\ufeffDATABASE_URL"):
    os.environ["DATABASE_URL"] = os.getenv("\ufeffDATABASE_URL")


def get_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


def get_cursor(conexion):
    return conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
