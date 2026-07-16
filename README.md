# 🤖 CSV Query Agent

AI-powered data analyst agent built with LangChain and LangGraph. Upload any CSV and query it using natural language — gets you SQL results and charts instantly.

## Demo: https://csv-query-agentgit-m2ts5ftehfolzcvwbskqbl.streamlit.app/
---

## Features

- 💬 **Natural language queries** — ask questions in plain English, get SQL results back
- 📊 **Auto-generated charts** — bar, line, pie, scatter, histogram charts on demand
- 🔐 **User authentication** — login, register, sessions per user
- 🗂️ **Persistent chat history** — previous chats saved, renameable and deletable
---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent Framework | LangGraph + LangChain |
| LLM | OpenAI GPT-OSS 20B via Groq |
| Database | SQLite |
| Charts | Plotly |
| UI | Streamlit |
| Language | Python |

---

## How It Works

1. User uploads a CSV file
2. CSV is loaded into a SQLite database
3. LangGraph ReAct agent receives the user's question
4. Agent calls `execute_sql_query` to fetch data
5. Agent calls `create_chart` if a visualization is requested
6. Results and charts are displayed in the chat interface

---


## Project Structure

```
data-chat/
├── app.py              # Streamlit UI
├── graph.py            # LangGraph ReAct agent
├── db.py               # CSV → SQLite loader
├── sql_tool.py         # SQL execution tool
├── chart_tool.py       # Chart generation tool
├── chat_store.py       # Auth + persistent chat history
└── requirements.txt
```

---

## Example Queries

- `show me the first 10 rows`
- `what is total sales by region as a bar chart`
- `which product category has the highest revenue`
- `compare online vs retail sales channel as a pie chart`
- `calculate profit per category using unit price minus unit cost`

## Limitations

**Groq Free Tier Rate Limits**

This app uses Groq's free tier which has a limit of **8,000 tokens per minute**.
Each question the agent answers consumes roughly 2,000–4,000 tokens
(schema call + SQL query + response). This means:

- You may hit the limit after 2–3 quick questions
- If you see a rate limit error, wait 60 seconds and try again
- Large datasets with complex queries consume more tokens

