from langgraph.prebuilt import create_react_agent
from langchain_groq import ChatGroq

SYSTEM_PROMPT = """You are a data analyst. Table name: uploaded_data.
Always call get_table_schema first, then execute_sql_query, then create_chart if needed.
Use SQLite syntax only."""



def create_agent(tools: list):
    llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)


    agent = create_react_agent(model=llm, tools=tools, prompt=SYSTEM_PROMPT)
    return agent