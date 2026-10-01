import sqlite3
import os
from config import Config

def get_db_connection():
    if Config.USE_MYSQL:
        try:
            import pymysql
            conn = pymysql.connect(
                host=Config.MYSQL_HOST,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD,
                database=Config.MYSQL_DB,
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
            return conn
        except Exception as e:
            print(f"[Database Warning] MySQL connection failed: {e}. Falling back to SQLite.")

    # SQLite connection with dict row factory
    conn = sqlite3.connect(Config.SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def execute_query(query, params=(), fetch_one=False, fetch_all=False, commit=False):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        if commit:
            conn.commit()
            last_id = cursor.lastrowid
            return last_id
        if fetch_one:
            row = cursor.fetchone()
            return dict(row) if row else None
        if fetch_all:
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        return None
    finally:
        cursor.close()
        conn.close()

def init_db():
    """Initializes tables from schema.sql if they do not exist."""
    schema_path = os.path.join(Config.BASE_DIR, 'database', 'schema.sql')
    if not os.path.exists(schema_path):
        return

    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # SQLite executescript
        if hasattr(cursor, 'executescript'):
            cursor.executescript(schema_sql)
            conn.commit()
        else:
            for statement in schema_sql.split(';'):
                stmt = statement.strip()
                if stmt:
                    cursor.execute(stmt)
            conn.commit()
    finally:
        cursor.close()
        conn.close()
    
    # Ensure uploads subdirectories exist
    os.makedirs(os.path.join(Config.UPLOAD_FOLDER, 'reports'), exist_ok=True)
    os.makedirs(os.path.join(Config.UPLOAD_FOLDER, 'resolutions'), exist_ok=True)
