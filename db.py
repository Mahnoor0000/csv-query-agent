import sqlite3
import pandas as pd

TABLE_NAME = "uploaded_data"
_db_path = None


def set_db_path(path: str):
    global _db_path
    _db_path = path


def load_csv(file, db_path: str) -> pd.DataFrame:
    global _db_path
    df = pd.read_csv(file)
    conn = sqlite3.connect(db_path)
    df.to_sql(TABLE_NAME, conn, if_exists="replace", index=False)
    conn.close()
    _db_path = db_path
    return df


def get_schema() -> str:
    if not _db_path:
        return "No database loaded."
    conn = sqlite3.connect(_db_path)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
    columns = cursor.fetchall()
    cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
    count = cursor.fetchone()[0]
    conn.close()
    schema = f"Table: {TABLE_NAME} ({count} rows)\nColumns:\n"
    for col in columns:
        schema += f"  - {col[1]} (type: {col[2]})\n"
    return schema


def run_query(query: str) -> pd.DataFrame:
    if not _db_path:
        raise RuntimeError("No database loaded.")
    conn = sqlite3.connect(_db_path)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df