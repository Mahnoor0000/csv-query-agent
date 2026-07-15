import plotly.express as px
from langchain_core.tools import tool
from db import run_query

# Streamlit reads this dict after agent finishes to display charts
CHART_REGISTRY = {}


def clear_charts():
    CHART_REGISTRY.clear()


@tool
def create_chart(sql_query: str, chart_type: str, x_column: str, y_column: str, title: str) -> str:
    """Create a chart from SQL query results and display it to the user.
    
    Args:
        sql_query:  SQL query to fetch data for the chart.
        chart_type: Type of chart: bar, line, scatter, pie, histogram, box
        x_column:   Column for X axis (use 'names' for pie chart)
        y_column:   Column for Y axis (use 'values' for pie chart)
        title:      Title of the chart
    """
    try:
        df = run_query(sql_query)

        if df.empty:
            return "No data returned for chart."

        chart_type = chart_type.lower()

        if chart_type == "bar":
            fig = px.bar(df, x=x_column, y=y_column, title=title)
        elif chart_type == "line":
            fig = px.line(df, x=x_column, y=y_column, title=title)
        elif chart_type == "scatter":
            fig = px.scatter(df, x=x_column, y=y_column, title=title)
        elif chart_type == "pie":
            fig = px.pie(df, names=x_column, values=y_column, title=title)
        elif chart_type == "histogram":
            fig = px.histogram(df, x=x_column, title=title)
        elif chart_type == "box":
            fig = px.box(df, x=x_column, y=y_column, title=title)
        else:
            fig = px.bar(df, x=x_column, y=y_column, title=title)

        # store chart so Streamlit can render it
        chart_id = f"chart_{len(CHART_REGISTRY) + 1}"
        CHART_REGISTRY[chart_id] = fig.to_json()

        return f"Chart '{title}' created successfully."

    except Exception as e:
        return f"Chart Error: {str(e)}"