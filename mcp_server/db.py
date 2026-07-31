import pymysql
import pymysql.cursors

DB_CONFIG = {
    "host": "localhost",
    "user": "your_user",
    "password": "your_password",
    "database": "swiftrail_db",
    "cursorclass": pymysql.cursors.DictCursor,
}

def get_connection():
    try:
        conn = pymysql.connect(**DB_CONFIG)
        return conn
    except pymysql.MySQLError as e:
        raise RuntimeError(f"Database connection failed: {e}")