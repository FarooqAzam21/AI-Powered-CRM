import streamlit as st
import pandas as pd
import time
import json
import os
from datetime import datetime

# ================= IMPORTS =================
from classifier import classify_message
from responder import generate_reply
from priority_checker import check_priority
from title_generator import generate_title
from ticket_manager import generate_ticket
from auth.auth_manager import authenticate
from analytics import load_tickets
from sla_manager import check_sla
from escalation_manager import escalate_ticket

# ================= FILES =================
TICKET_FILE = "tickets.csv"
MESSAGE_FILE = "messages.csv"
AGENT_FILE = "agents.json"

# ================= HELPERS =================
def load_agents():
    with open(AGENT_FILE, "r") as f:
        return json.load(f)["support"]

def save_ticket(row_dict):
    df = pd.DataFrame([row_dict])

    if not os.path.exists(TICKET_FILE):
        df.to_csv(TICKET_FILE, index=False)
    else:
        df.to_csv(TICKET_FILE, mode="a", header=False, index=False)

def save_message(ticket_id, role, sender, message):
    row = {
        "TicketID": ticket_id,
        "Role": role,
        "Sender": sender,
        "Message": message,
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    df = pd.DataFrame([row])

    if not os.path.exists(MESSAGE_FILE):
        df.to_csv(MESSAGE_FILE, index=False)
    else:
        df.to_csv(MESSAGE_FILE, mode="a", header=False, index=False)

def load_messages(ticket_id):
    if not os.path.exists(MESSAGE_FILE):
        return pd.DataFrame()
    df = pd.read_csv(MESSAGE_FILE)
    return df[df["TicketID"] == ticket_id]

def auto_assign_agent():
    agents = load_agents()

    if not os.path.exists(TICKET_FILE):
        return agents[0]

    df = pd.read_csv(TICKET_FILE)
    counts = df["Agent"].value_counts().to_dict()
    agent_load = {a: counts.get(a, 0) for a in agents}

    return min(agent_load, key=agent_load.get)

# ================= STREAMLIT CONFIG =================
st.set_page_config("AI Support System", layout="wide")

# ================= SESSION =================
if "user" not in st.session_state:
    st.session_state.user = None

# ================= LOGIN =================
if st.session_state.user is None:
    st.title("🔐 Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = authenticate(email, password)
        if user:
            st.session_state.user = user
            st.rerun()
        else:
            st.error("Invalid credentials")

    st.stop()

# ================= APP CONTENT =================
# Extreme defensive check for incorrect startup (like uvicorn)
if st.session_state.user:
    user_obj = st.session_state.user
    role = user_obj.get("role", "user")
    user_email = user_obj.get("email", "")
    user_name = user_obj.get("name", "")

    st.sidebar.success(f"{user_name} ({role.upper()})")

    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

    # ================= NAV =================
    page = st.sidebar.radio(
        "Navigation",
        ["Support", "My Tickets", "Analytics"] if role == "admin" else ["Support", "My Tickets"]
    )
else:
    # This block should ideally not be reached due to st.stop() above,
    # but we include it for complete safety.
    st.title("Please Login")
    st.stop()

# ==================================================
# ================= CUSTOMER SUPPORT =================
# ==================================================
if page == "Support":

    st.title("💬 Customer Support")

    customer_id = st.text_input("Customer ID")
    message = st.chat_input("Type your message...")

    if message:

        start_time = time.time()

        category, confidence = classify_message(message)
        priority = check_priority(message)
        ticket_id, timestamp = generate_ticket()
        title = generate_title([], message, category)

        # Fetch history for context
        history = []
        if os.path.exists(MESSAGE_FILE):
            df_hist = pd.read_csv(MESSAGE_FILE)
            user_hist = df_hist[df_hist["Sender"] == customer_id].tail(5)
            history = user_hist.to_dict(orient="records")

        # BOT FIRST REPLY
        bot_reply = generate_reply(message, category, "empathetic", confidence, history)

        save_message(ticket_id, "user", customer_id, message)
        save_message(ticket_id, "bot", "AI-Bot", bot_reply)

        response_minutes = int((time.time() - start_time) / 60)
        sla_breached = check_sla(priority, response_minutes)
        escalation = escalate_ticket(priority, sla_breached)

        agent = auto_assign_agent()

        save_ticket({
            "TicketID": ticket_id,
            "Timestamp": timestamp,
            "Title": title,
            "Message": message,
            "Category": category,
            "Confidence": confidence,
            "Priority": escalation["new_priority"],
            "Agent": agent,
            "ResponseTime": response_minutes,
            "SLA_Breached": sla_breached,
            "Escalated": escalation["escalated"]
        })

        st.success("Ticket Created")
        st.chat_message("bot").write(bot_reply)

# ==================================================
# ================= AGENT VIEW ======================
# ==================================================
if page == "My Tickets":

    st.title("🧑‍💼 My Tickets")

    if not os.path.exists(TICKET_FILE):
        st.info("No tickets yet")
        st.stop()

    df = pd.read_csv(TICKET_FILE)
    my_tickets = df[df["Agent"] == user_email]

    if my_tickets.empty:
        st.info("No assigned tickets")
        st.stop()

    ticket_map = {
    f"{row['TicketID']} — {row['Title']}": row["TicketID"]
    for _, row in my_tickets.iterrows()
}

    selected_label = st.selectbox(
        "Select Ticket",
        list(ticket_map.keys())
    )

    ticket_id = ticket_map[selected_label]


    msgs = load_messages(ticket_id)

    for _, m in msgs.iterrows():
        with st.chat_message(m["Role"]):
            st.write(m["Message"])

    reply = st.chat_input("Reply to customer...")

    if reply:
        save_message(ticket_id, "agent", user_email, reply)
        st.rerun()

# ==================================================
# ================= ADMIN ANALYTICS =================
# ==================================================
if page == "Analytics" and role == "admin":

    st.title("📊 Admin Dashboard")

    if not os.path.exists(TICKET_FILE):
        st.info("No data")
        st.stop()

    df = pd.read_csv(TICKET_FILE)

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Tickets", len(df))
    c2.metric("Escalations", len(df[df["Escalated"] == True]))
    c3.metric("SLA Breaches", len(df[df["SLA_Breached"] == True]))

    st.subheader("All Tickets")
    st.dataframe(df, use_container_width=True)
