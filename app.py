import json
import streamlit as st
import plotly.io as pio
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

from db import load_csv, set_db_path
from chat_store import *
from sql_tool import get_table_schema, execute_sql_query
from chart_tool import create_chart, CHART_REGISTRY, clear_charts
from graph import create_agent

load_dotenv()
init_db()
st.set_page_config(page_title="CSV Analyst", page_icon="📊", layout="wide")

# ── Session defaults ──────────────────────────────────────────────────────────
for k, v in {"user_id": None, "username": None, "current_chat_id": None, "agent": None, "renaming_chat": None}.items():
    st.session_state.setdefault(k, v)

# ── Auth ──────────────────────────────────────────────────────────────────────
if not st.session_state.user_id:
    st.title("📊 CSV Analyst")
    t1, t2 = st.tabs(["Login", "Sign Up"])
    with t1:
        u, p = st.text_input("Username", key="lu"), st.text_input("Password", type="password", key="lp")
        if st.button("Login", type="primary"):
            uid = verify_user(u, p)
            if uid:
                st.session_state.update(user_id=uid, username=u); st.rerun()
            else:
                st.error("Invalid credentials.")
    with t2:
        u2, p2 = st.text_input("Username", key="ru"), st.text_input("Password", type="password", key="rp")
        if st.button("Sign Up", type="primary"):
            st.success("Account created! Login now.") if create_user(u2, p2) else st.error("Username taken.")
    st.stop()

# ── Helpers ───────────────────────────────────────────────────────────────────
def init_agent():
    st.session_state.agent = create_agent([get_table_schema, execute_sql_query, create_chart])

def load_chat(chat_id):
    st.session_state.current_chat_id = chat_id
    chat = get_chat(chat_id)
    if chat and chat["csv_db_path"]:
        set_db_path(chat["csv_db_path"])
    init_agent()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"👤 **{st.session_state.username}**")
    if st.button("Logout", use_container_width=True):
        st.session_state.clear(); st.rerun()
    st.divider()
    if st.button("➕ New Chat", type="primary", use_container_width=True):
        load_chat(create_chat(st.session_state.user_id)); st.rerun()
    st.divider()
    st.subheader("Chats")
    for chat in get_user_chats(st.session_state.user_id):
        if st.session_state.renaming_chat == chat["id"]:
            t = st.text_input("", value=chat["title"], key=f"ri_{chat['id']}")
            c1, c2 = st.columns(2)
            if c1.button("Save", key=f"sv_{chat['id']}"):
                update_chat_title(chat["id"], t); st.session_state.renaming_chat = None; st.rerun()
            if c2.button("Cancel", key=f"cx_{chat['id']}"):
                st.session_state.renaming_chat = None; st.rerun()
        else:
            c1, c2, c3 = st.columns([5, 1, 1])
            label = f"**{chat['title']}**" if chat["id"] == st.session_state.current_chat_id else chat["title"]
            if c1.button(label, key=f"ch_{chat['id']}", use_container_width=True):
                load_chat(chat["id"]); st.rerun()
            if c2.button("✏️", key=f"rn_{chat['id']}"):
                st.session_state.renaming_chat = chat["id"]; st.rerun()
            if c3.button("🗑️", key=f"dl_{chat['id']}"):
                delete_chat(chat["id"])
                if st.session_state.current_chat_id == chat["id"]:
                    st.session_state.update(current_chat_id=None, agent=None)
                st.rerun()

# ── Main ──────────────────────────────────────────────────────────────────────
if not st.session_state.current_chat_id:
    st.title("📊 CSV Analyst"); st.info("👈 Click **New Chat** to get started."); st.stop()

chat = get_chat(st.session_state.current_chat_id)
st.title(chat["title"] if chat else "Chat")

if not chat or not chat["csv_db_path"]:
    st.subheader("📁 Upload a CSV to begin")
    f = st.file_uploader("Choose a CSV", type="csv")
    if f:
        db_path = f"csv_{st.session_state.current_chat_id}.db"
        df = load_csv(f, db_path)
        update_chat_csv(st.session_state.current_chat_id, f.name, db_path)
        update_chat_title(st.session_state.current_chat_id, f.name.replace(".csv","").replace("_"," ").title())
        init_agent()
        st.success(f"✅ {len(df)} rows × {len(df.columns)} columns"); st.rerun()
    st.stop()

if not st.session_state.agent:
    init_agent()

# ── Chat ──────────────────────────────────────────────────────────────────────
messages = get_chat_messages(st.session_state.current_chat_id)
for msg in messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["charts_json"]:
            for cj in json.loads(msg["charts_json"]):
                st.plotly_chart(pio.from_json(cj), use_container_width=True)

if prompt := st.chat_input("Ask anything about your data..."):
    with st.chat_message("user"): st.markdown(prompt)
    save_message(st.session_state.current_chat_id, "user", prompt)

    history = [HumanMessage(content=m["content"]) if m["role"] == "user" else AIMessage(content=m["content"]) for m in messages]
    history.append(HumanMessage(content=prompt))

    clear_charts()
    with st.chat_message("assistant"):
        try:
            result = st.session_state.agent.invoke({"messages": history})
            response = result["messages"][-1].content
            st.markdown(response)
            chart_jsons = []
            for cj in CHART_REGISTRY.values():
                st.plotly_chart(pio.from_json(cj), use_container_width=True)
                chart_jsons.append(cj)
            save_message(st.session_state.current_chat_id, "assistant", response, json.dumps(chart_jsons) if chart_jsons else None)
        except Exception as e:
            st.error(f"Error: {e}")