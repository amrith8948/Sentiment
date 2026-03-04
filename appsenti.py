import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import json

# ---------------- CONFIG ---------------- #

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

GROQ_MODEL = "llama3-70b-8192"

supabase_headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# ---------------- LEAD TEMPERATURE ---------------- #

def lead_temperature(message):
    text = message.lower()

    if any(word in text for word in ["scared", "fear", "confused", "worried"]):
        return "HOT 🔥"
    elif any(word in text for word in ["interested", "planning", "thinking"]):
        return "WARM 🌤"
    else:
        return "COLD ❄"

# ---------------- GROQ AI RESPONSE ---------------- #

def generate_response(user_input):

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": "You are a helpful academic counsellor from Kerala."},
            {"role": "user", "content": user_input}
        ],
        "temperature": 0.8,
        "max_tokens": 300
    }

    response = requests.post(url, headers=headers, json=payload)

    st.write("STATUS CODE:", response.status_code)
    st.write("RAW RESPONSE:", response.text)

    if response.status_code == 200:
        result = response.json()
        return result["choices"][0]["message"]["content"]

    return "API Failed"
def fallback_reply():
    return (
        "ACCA, CA, and CMA are strong professional courses. "
        "The right option depends on your goals.\n\n"
        "Would you like to book a FREE career guidance call?"
    )

# ---------------- SUPABASE UPSERT ---------------- #

def upsert_chat(phone, data):

    check_url = f"{SUPABASE_URL}/rest/v1/chats?phone=eq.{phone}"
    response = requests.get(check_url, headers=supabase_headers)

    if response.status_code == 200 and response.json():
        update_url = f"{SUPABASE_URL}/rest/v1/chats?phone=eq.{phone}"
        requests.patch(update_url, headers=supabase_headers, json=data)
    else:
        insert_url = f"{SUPABASE_URL}/rest/v1/chats"
        requests.post(insert_url, headers=supabase_headers, json=data)

# ---------------- STREAMLIT UI ---------------- #

st.set_page_config(page_title="Kerala Academic Counsellor", layout="centered")
st.title("🎓 Kerala Career Guidance AI")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "user_info" not in st.session_state:
    st.session_state.user_info = False

# Collect Lead Info First
if not st.session_state.user_info:
    with st.form("lead_form"):
        name = st.text_input("Your Name")
        phone = st.text_input("Phone Number")
        submitted = st.form_submit_button("Start Chat")

        if submitted:
            if name and phone:
                st.session_state.name = name
                st.session_state.phone = phone
                st.session_state.user_info = True
                st.rerun()
            else:
                st.error("Please enter all details")

# Chat Interface
if st.session_state.user_info:

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Ask your career question...")

    if user_input:

        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("user"):
            st.markdown(user_input)

        bot_reply = generate_response(user_input)
        lead_status = lead_temperature(user_input)

        st.session_state.messages.append({"role": "assistant", "content": bot_reply})

        with st.chat_message("assistant"):
            st.markdown(bot_reply)
            st.info(f"Lead Priority: {lead_status}")

        data = {
            "name": st.session_state.name,
            "phone": st.session_state.phone,
            "conversation": st.session_state.messages,
            "lead_status": lead_status,
            "created_at": datetime.utcnow().isoformat()
        }

        upsert_chat(st.session_state.phone, data)

# ---------------- ADMIN PANEL ---------------- #

st.markdown("---")
if st.checkbox("Admin Login"):
    pin = st.text_input("Enter 4-digit PIN", type="password")
    if pin == "8948":
        url = f"{SUPABASE_URL}/rest/v1/chats?select=*"
        response = requests.get(url, headers=supabase_headers)
        if response.status_code == 200:
            df = pd.DataFrame(response.json())
            st.dataframe(df)
        else:
            st.error("Failed to fetch data")
