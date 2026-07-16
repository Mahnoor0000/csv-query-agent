from langchain_core.tools import tool
from db import get_schema, run_query


@tool
def get_table_schema() -> str:
    """Get the schema of the uploaded CSV table. 
    Always call this first before writing any SQL query."""
    return get_schema()


@tool
def execute_sql_query(query: str) -> str:
    """Execute a SQL SELECT query on the uploaded CSV data.
    Table name is always 'uploaded_data'.
    Only SELECT queries are allowed.
    Use SQLite syntax.

    Args:
        query: A valid SQLite SELECT statement.
    """
    # block dangerous queries
    forbidden = ["drop", "delete", "update", "insert", "alter"]
    if any(word in query.lower() for word in forbidden):
        return "Error: Only SELECT queries are allowed."

    try:
        # run the SQL against the current chat's SQLite file via db.py
        df = run_query(query)
        if df.empty:
            return "Query returned no results."
        # convert results to markdown table so the agent can read them as text
        return df.head(100).to_markdown(index=False)
    except Exception as e:
        return f"SQL Error: {str(e)}"