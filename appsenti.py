import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import json

# ---------------- CONFIG ---------------- #

HF_TOKEN = st.secrets["HF_TOKEN"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

MODEL = "j-hartmann/emotion-english-distilroberta-base"

supabase_headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# ---------------- EMOTION ---------------- #

def detect_emotion(text):
    API_URL = f"https://router.huggingface.co/hf-inference/models/{MODEL}"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {"inputs": text}

    response = requests.post(API_URL, headers=headers, json=payload)
    result = response.json()

    if isinstance(result, list):
        emotions = result[0]
        top = max(emotions, key=lambda x: x["score"])
        return top["label"]
    return "neutral"

# ---------------- LEAD TEMP ---------------- #

def lead_temperature(emotion):
    if emotion in ["fear", "sadness"]:
        return "HOT 🔥"
    elif emotion == "joy":
        return "WARM 🌤"
    return "COLD ❄"

# ---------------- SMART RESPONSE ---------------- #

def generate_response(user_input, emotion):

    text = user_input.lower()

    # Course detection
    if "acca" in text:
        course = "ACCA (Global Recognition 🌍)"
    elif "ca" in text:
        course = "CA (Strong India Value 🇮🇳)"
    elif "cma" in text:
        course = "CMA (Corporate Career 💼)"
    else:
        course = "ACCA / CA / CMA"

    emotional_prefix = ""

    if emotion == "fear":
        emotional_prefix = "I understand you're feeling uncertain. "
    elif emotion == "sadness":
        emotional_prefix = "It sounds like you're confused. "
    elif emotion == "anger":
        emotional_prefix = "I understand the frustration. "
    elif emotion == "joy":
        emotional_prefix = "I love your confidence! "

    return (
        emotional_prefix +
        f"\n\nRegarding {course}, many Kerala students choose this after +2 or graduation."
        "\n\nWith proper mentorship, first-attempt success becomes realistic."
        "\n\n🎓 We provide:\n"
        "✔ Malayalam + English Support\n"
        "✔ Small Batches\n"
        "✔ Personal Mentor\n"
        "✔ Placement Guidance (Kerala & GCC)\n\n"
        "Would you like to book a FREE career guidance call?"
    )

# ---------------- SUPABASE UPSERT ---------------- #

def upsert_chat(phone, data):

    url = f"{SUPABASE_URL}/rest/v1/chats?phone=eq.{phone}"

    response = requests.get(url, headers=supabase_headers)

    if response.status_code == 200 and response.json():
        # Update existing row
        update_url = f"{SUPABASE_URL}/rest/v1/chats?phone=eq.{phone}"
        requests.patch(update_url, headers=supabase_headers, json=data)
    else:
        # Insert new row
        insert_url = f"{SUPABASE_URL}/rest/v1/chats"
        requests.post(insert_url, headers=supabase_headers, json=data)

# ---------------- UI ---------------- #

st.set_page_config(page_title="Kerala Academic Counsellor")

st.title("🎓 Kerala Career Guidance AI")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "user_info" not in st.session_state:
    st.session_state.user_info = False

if not st.session_state.user_info:
    with st.form("lead"):
        name = st.text_input("Your Name")
        phone = st.text_input("Phone Number")
        submit = st.form_submit_button("Start Chat")

        if submit:
            if name and phone:
                st.session_state.name = name
                st.session_state.phone = phone
                st.session_state.user_info = True
                st.rerun()
            else:
                st.error("Fill all fields")

if st.session_state.user_info:

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Ask your career question...")

    if user_input:

        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("user"):
            st.markdown(user_input)

        emotion = detect_emotion(user_input)
        reply = generate_response(user_input, emotion)
        lead_status = lead_temperature(emotion)

        st.session_state.messages.append({"role": "assistant", "content": reply})

        with st.chat_message("assistant"):
            st.markdown(reply)
            st.info(f"Lead Priority: {lead_status}")

        # Save full conversation as JSON
        data = {
            "name": st.session_state.name,
            "phone": st.session_state.phone,
            "conversation": st.session_state.messages,
            "last_emotion": emotion,
            "lead_status": lead_status
        }

        upsert_chat(st.session_state.phone, data)

# ---------------- ADMIN ---------------- #

st.markdown("---")
if st.checkbox("Admin Login"):
    pin = st.text_input("Enter PIN", type="password")
    if pin == "8948":
        url = f"{SUPABASE_URL}/rest/v1/chats?select=*"
        response = requests.get(url, headers=supabase_headers)
        if response.status_code == 200:
            df = pd.DataFrame(response.json())
            st.dataframe(df)
