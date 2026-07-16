import sqlite3
import pandas as pd

# name of the SQL table inside every chat's SQLite file
TABLE_NAME = "uploaded_data"

# db.py needs to know which file to connect to when the agent runs a query
_db_path = None    # stores path of csv for current chat



def set_db_path(path: str):
    global _db_path
    # set when switching to a previous chat
    _db_path = path        


def load_csv(file, db_path: str) -> pd.DataFrame:
    global _db_path
    # convert csv to pandas dataframe
    try:
        df = pd.read_csv(file, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(file, encoding="latin-1")
    # make sqlite connection for db_path
    conn = sqlite3.connect(db_path)  
    # write dataframe in sqlite
    df.to_sql(TABLE_NAME, conn, if_exists="replace", index=False)  
    # close connection
    conn.close()
    _db_path = db_path
    return df


def get_schema() -> str:

    # returns column names and types as string so agent knows what kinda data exist before writing queries
    if not _db_path:
        return "No database loaded."
    conn = sqlite3.connect(_db_path)
    cursor = conn.cursor()
    # return one row per column
    cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
    columns = cursor.fetchall()
    # return total row count 
    cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
    count = cursor.fetchone()[0]
    conn.close()
    # readable string llm can understanf
    schema = f"Table: {TABLE_NAME} ({count} rows)\nColumns:\n"
    for col in columns:
        schema += f"  - {col[1]} (type: {col[2]})\n"
    return schema


def run_query(query: str) -> pd.DataFrame:
    # execute any select sql query
    if not _db_path:
        raise RuntimeError("No database loaded.")
    conn = sqlite3.connect(_db_path)
    # return query results as pandas dataframe
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df
    