import os
from pathlib import Path
from dotenv import load_dotenv
import pymysql
import pymysql.cursors

# Load environment variables from .env
load_dotenv(Path(__file__).parent / ".env")

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "database": os.environ.get("DB_NAME", "swiftrail_db"),
    "cursorclass": pymysql.cursors.DictCursor,
}

def get_connection():
    try:
        return pymysql.connect(**DB_CONFIG)
    except pymysql.MySQLError as e:
        raise RuntimeError(f"Database connection failed: {e}")