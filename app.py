import streamlit as st
import plotly.io as pio
import json
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk

from db import load_csv, get_schema, set_db_path
from chat_store import (
    init_db, verify_user, create_user,
    get_user_chats, create_chat, delete_chat,
    update_chat_title, update_chat_csv, get_chat,
    save_message, get_chat_messages
)
from sql_tool import get_table_schema, execute_sql_query
from chart_tool import create_chart, CHART_REGISTRY, clear_charts
from graph import create_agent

load_dotenv()
init_db()

st.set_page_config(page_title="CSV Analyst", page_icon="📊", layout="wide")

# ── Session defaults ──────────────────────────────────────────────────────────
for key, val in {
    "user_id": None, "username": None,
    "current_chat_id": None, "agent": None,
    "renaming_chat": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ─────────────────────────────────────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.user_id:
    st.title("📊 CSV Data Analyst")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login", type="primary"):
            user_id = verify_user(username, password)
            if user_id:
                st.session_state.user_id = user_id
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Invalid username or password.")

    with tab2:
        new_user = st.text_input("Choose Username", key="reg_user")
        new_pass = st.text_input("Choose Password", type="password", key="reg_pass")
        if st.button("Create Account", type="primary"):
            if create_user(new_user, new_pass):
                st.success("Account created! Please login.")
            else:
                st.error("Username already taken.")

    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def init_agent():
    tools = [get_table_schema, execute_sql_query, create_chart]
    st.session_state.agent = create_agent(tools)


def load_chat(chat_id: str):
    st.session_state.current_chat_id = chat_id
    chat = get_chat(chat_id)
    if chat and chat["csv_db_path"]:
        set_db_path(chat["csv_db_path"])
    init_agent()


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"👤 **{st.session_state.username}**")
    if st.button("Logout", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    st.divider()

    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        chat_id = create_chat(st.session_state.user_id)
        load_chat(chat_id)
        st.rerun()

    st.divider()
    st.subheader("Chats")

    chats = get_user_chats(st.session_state.user_id)

    for chat in chats:
        is_active = chat["id"] == st.session_state.current_chat_id

        # Rename mode
        if st.session_state.renaming_chat == chat["id"]:
            new_title = st.text_input("", value=chat["title"], key=f"ri_{chat['id']}")
            c1, c2 = st.columns(2)
            if c1.button("Save", key=f"sv_{chat['id']}"):
                update_chat_title(chat["id"], new_title)
                st.session_state.renaming_chat = None
                st.rerun()
            if c2.button("Cancel", key=f"cx_{chat['id']}"):
                st.session_state.renaming_chat = None
                st.rerun()
        else:
            col1, col2, col3 = st.columns([5, 1, 1])
            label = f"**{chat['title']}**" if is_active else chat["title"]
            if col1.button(label, key=f"ch_{chat['id']}", use_container_width=True):
                load_chat(chat["id"])
                st.rerun()
            if col2.button("✏️", key=f"rn_{chat['id']}"):
                st.session_state.renaming_chat = chat["id"]
                st.rerun()
            if col3.button("🗑️", key=f"dl_{chat['id']}"):
                delete_chat(chat["id"])
                if st.session_state.current_chat_id == chat["id"]:
                    st.session_state.current_chat_id = None
                    st.session_state.agent = None
                st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# MAIN AREA
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.current_chat_id:
    st.title("📊 CSV Data Analyst")
    st.info("👈 Click **New Chat** to get started.")
    st.stop()

chat = get_chat(st.session_state.current_chat_id)
st.title(chat["title"] if chat else "Chat")

# ── CSV Upload (only when this chat has no CSV yet) ───────────────────────────
if not chat or not chat["csv_db_path"]:
    st.subheader("📁 Upload a CSV to begin")
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

    if uploaded_file:
        db_path = f"csv_{st.session_state.current_chat_id}.db"
        df = load_csv(uploaded_file, db_path)
        update_chat_csv(st.session_state.current_chat_id, uploaded_file.name, db_path)

        # auto-name chat from filename
        title = uploaded_file.name.replace(".csv", "").replace("_", " ").title()
        update_chat_title(st.session_state.current_chat_id, title)

        init_agent()
        st.success(f"✅ Loaded {len(df)} rows × {len(df.columns)} columns")
        st.rerun()
    st.stop()

# ── Ensure agent is initialised ───────────────────────────────────────────────
if not st.session_state.agent:
    init_agent()

# ── Render chat history ───────────────────────────────────────────────────────
messages = get_chat_messages(st.session_state.current_chat_id)

for msg in messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["charts_json"]:
            for chart_json in json.loads(msg["charts_json"]):
                st.plotly_chart(pio.from_json(chart_json), use_container_width=True)

# ── Input & streaming response ────────────────────────────────────────────────
prompt = st.chat_input("Ask anything about your data...")

if prompt:
    # show + persist user message
    with st.chat_message("user"):
        st.markdown(prompt)
    save_message(st.session_state.current_chat_id, "user", prompt)

    # build full history for agent
    history = []
    for msg in messages:
        cls = HumanMessage if msg["role"] == "user" else AIMessage
        history.append(cls(content=msg["content"]))
    history.append(HumanMessage(content=prompt))

    # stream assistant response
    clear_charts()
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""

        try:
            result = st.session_state.agent.invoke({"messages": history})
            full_response = result["messages"][-1].content
            placeholder.markdown(full_response)

            # render + collect charts
            chart_jsons = []
            for chart_json in CHART_REGISTRY.values():
                st.plotly_chart(pio.from_json(chart_json), use_container_width=True)
                chart_jsons.append(chart_json)

            # persist assistant message
            charts_str = json.dumps(chart_jsons) if chart_jsons else None
            save_message(st.session_state.current_chat_id, "assistant", full_response, charts_str)

        except Exception as e:
            st.error(f"Error: {str(e)}")