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

# create chat_store.db with users, chats, messages tables if they don't exist
init_db()

st.set_page_config(page_title="CSV Analyst", page_icon="📊", layout="wide")

# ── Session defaults ──────────────────────────────────────────────────────────
# streamlit reruns the entire file on every click
# session_state survives reruns — it's how we keep data alive between interactions
# setdefault only sets value if key doesn't already exist — won't overwrite existing data
for k, v in {"user_id": None, "username": None, "current_chat_id": None, "agent": None, "renaming_chat": None}.items():
    st.session_state.setdefault(k, v)

# ── Auth ──────────────────────────────────────────────────────────────────────
# if user_id is None the user is not logged in — show login screen
if not st.session_state.user_id:
    st.title("📊 CSV Analyst")
    t1, t2 = st.tabs(["Login", "Sign Up"])

    with t1:
        u, p = st.text_input("Username", key="lu"), st.text_input("Password", type="password", key="lp")
        if st.button("Login", type="primary"):
            uid = verify_user(u, p)  # checks username + hashed password against SQLite
            if uid:
                # save user info to session state and rerun
                # on rerun user_id exists so this block is skipped
                st.session_state.update(user_id=uid, username=u); st.rerun()
            else:
                st.error("Invalid credentials.")

    with t2:
        u2, p2 = st.text_input("Username", key="ru"), st.text_input("Password", type="password", key="rp")
        if st.button("Sign Up", type="primary"):
            # create_user returns True if successful, False if username already taken
            st.success("Account created! Login now.") if create_user(u2, p2) else st.error("Username taken.")

    # stop execution here — nothing below runs until user is logged in
    st.stop()

# ── Helpers ───────────────────────────────────────────────────────────────────
def init_agent():
    # creates a fresh LangGraph ReAct agent with the 3 tools
    # saved to session state so it persists across reruns
    st.session_state.agent = create_agent([get_table_schema, execute_sql_query, create_chart])


def load_chat(chat_id):
    # called when user clicks a chat in sidebar or creates a new one
    st.session_state.current_chat_id = chat_id
    chat = get_chat(chat_id)  # fetch chat details from chat_store.db
    if chat and chat["csv_db_path"]:
        # point db.py to this chat's SQLite file so queries hit the right CSV data
        set_db_path(chat["csv_db_path"])
    init_agent()  # create fresh agent for this chat


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"👤 **{st.session_state.username}**")

    if st.button("Logout", use_container_width=True):
        # wipe everything from session state
        # on rerun user_id is None so login screen shows
        st.session_state.clear(); st.rerun()

    st.divider()

    if st.button("➕ New Chat", type="primary", use_container_width=True):
        # create_chat inserts new row in SQLite and returns the UUID
        # load_chat sets it as active and creates the agent
        load_chat(create_chat(st.session_state.user_id)); st.rerun()

    st.divider()
    st.subheader("Chats")

    # fetch all chats for this user ordered by most recently used
    for chat in get_user_chats(st.session_state.user_id):

        if st.session_state.renaming_chat == chat["id"]:
            # this chat is in rename mode — show text input instead of button
            t = st.text_input("", value=chat["title"], key=f"ri_{chat['id']}")
            c1, c2 = st.columns(2)
            if c1.button("Save", key=f"sv_{chat['id']}"):
                # save new title to SQLite and exit rename mode
                update_chat_title(chat["id"], t); st.session_state.renaming_chat = None; st.rerun()
            if c2.button("Cancel", key=f"cx_{chat['id']}"):
                # exit rename mode without saving
                st.session_state.renaming_chat = None; st.rerun()
        else:
            # normal mode — show chat button with rename and delete buttons
            c1, c2, c3 = st.columns([5, 1, 1])

            # bold the active chat title so user knows which one is selected
            label = f"**{chat['title']}**" if chat["id"] == st.session_state.current_chat_id else chat["title"]

            if c1.button(label, key=f"ch_{chat['id']}", use_container_width=True):
                # switch to this chat
                load_chat(chat["id"]); st.rerun()

            if c2.button("✏️", key=f"rn_{chat['id']}"):
                # enter rename mode for this chat
                st.session_state.renaming_chat = chat["id"]; st.rerun()

            if c3.button("🗑️", key=f"dl_{chat['id']}"):
                # delete chat and all its messages from SQLite
                delete_chat(chat["id"])
                # if deleted chat was the active one, clear it from session state
                if st.session_state.current_chat_id == chat["id"]:
                    st.session_state.update(current_chat_id=None, agent=None)
                st.rerun()

# ── Main ──────────────────────────────────────────────────────────────────────
# no chat selected yet — show welcome message and stop
if not st.session_state.current_chat_id:
    st.title("📊 CSV Analyst"); st.info("👈 Click **New Chat** to get started."); st.stop()

# fetch current chat details from SQLite
chat = get_chat(st.session_state.current_chat_id)
st.title(chat["title"] if chat else "Chat")

# ── CSV Upload ────────────────────────────────────────────────────────────────
# this chat has no CSV uploaded yet — show upload screen
if not chat or not chat["csv_db_path"]:
    st.subheader("📁 Upload a CSV to begin")
    f = st.file_uploader("Choose a CSV", type="csv")
    if f:
        # each chat gets its own SQLite file named after its UUID
        db_path = f"csv_{st.session_state.current_chat_id}.db"

        # read CSV → write to SQLite as 'uploaded_data' table → set _db_path
        df = load_csv(f, db_path)

        # save filename and db path to chat_store.db so it persists across sessions
        update_chat_csv(st.session_state.current_chat_id, f.name, db_path)

        # auto-name chat from filename: "sales_data.csv" → "Sales Data"
        update_chat_title(st.session_state.current_chat_id, f.name.replace(".csv","").replace("_"," ").title())

        init_agent()
        st.success(f"✅ {len(df)} rows × {len(df.columns)} columns"); st.rerun()

    # stop here until CSV is uploaded — don't show chat interface yet
    st.stop()

# safety net — recreate agent if it got lost somehow
if not st.session_state.agent:
    init_agent()

# ── Chat History ──────────────────────────────────────────────────────────────
# fetch all saved messages for this chat from SQLite
messages = get_chat_messages(st.session_state.current_chat_id)

# re-render every message on each rerun so chat history stays visible
for msg in messages:
    with st.chat_message(msg["role"]):  # "user" or "assistant" bubble
        st.markdown(msg["content"])
        if msg["charts_json"]:
            # charts were saved as JSON strings — convert back to Plotly figures and render
            for cj in json.loads(msg["charts_json"]):
                st.plotly_chart(pio.from_json(cj), use_container_width=True)

# ── User Input ────────────────────────────────────────────────────────────────
# walrus operator — shows input box, waits, assigns to prompt, checks not empty
if prompt := st.chat_input("Ask anything about your data..."):

    # show and immediately save user message to SQLite
    with st.chat_message("user"): st.markdown(prompt)
    save_message(st.session_state.current_chat_id, "user", prompt)

    # convert all saved messages to LangChain message objects
    # agent needs this format — not plain dicts
    # full history sent every time so agent has context of entire conversation
    history = [HumanMessage(content=m["content"]) if m["role"] == "user" else AIMessage(content=m["content"]) for m in messages]
    history.append(HumanMessage(content=prompt))  # add current question at the end

    # empty CHART_REGISTRY so old charts don't bleed into this response
    clear_charts()

    with st.chat_message("assistant"):
        try:
            # run the full LangGraph ReAct loop:
            # agent thinks → calls tools → sees results → thinks → calls tools → final answer
            result = st.session_state.agent.invoke({"messages": history})

            # [-1] gets the last message — the agent's final text response
            response = result["messages"][-1].content
            st.markdown(response)

            # after agent finishes, render any charts it created
            # agent stored them in CHART_REGISTRY during create_chart tool calls
            chart_jsons = []
            for cj in CHART_REGISTRY.values():
                st.plotly_chart(pio.from_json(cj), use_container_width=True)
                chart_jsons.append(cj)  # collect for saving to SQLite

            # save assistant response + charts to SQLite for persistence
            # json.dumps converts list of chart JSONs to a single string for storage
            # None if no charts were created
            save_message(st.session_state.current_chat_id, "assistant", response, json.dumps(chart_jsons) if chart_jsons else None)

        except Exception as e:
            # show error in UI instead of crashing the app
            st.error(f"Error: {e}")