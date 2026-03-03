import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import json

# ---------------- CONFIG ---------------- #

HF_TOKEN = st.secrets["HF_TOKEN"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

EMOTION_MODEL = "j-hartmann/emotion-english-distilroberta-base"
GEN_MODEL = "mistralai/Mistral-7B-Instruct-v0.2"

supabase_headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# ---------------- EMOTION DETECTION ---------------- #

def detect_emotion(text):
    API_URL = f"https://router.huggingface.co/hf-inference/models/{EMOTION_MODEL}"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {"inputs": text}

    response = requests.post(API_URL, headers=headers, json=payload)
    result = response.json()

    if isinstance(result, list):
        emotions = result[0]
        top = max(emotions, key=lambda x: x["score"])
        return top["label"]

    return "neutral"

# ---------------- LEAD TEMPERATURE ---------------- #

def lead_temperature(emotion):
    if emotion in ["fear", "sadness"]:
        return "HOT 🔥"
    elif emotion == "joy":
        return "WARM 🌤"
    return "COLD ❄"

# ---------------- AI GENERATED RESPONSE ---------------- #

def generate_response(user_input, emotion):

    API_URL = f"https://router.huggingface.co/hf-inference/models/{GEN_MODEL}"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}

    system_prompt = f"""
You are a highly professional academic counsellor from Kerala.
You help students decide between ACCA, CA, and CMA.

Student Emotion: {emotion}

Instructions:
- Answer specifically to the student question.
- Be conversational and natural.
- Use Kerala context where relevant.
- Encourage booking a free career counselling call.
- Keep response under 180 words.
- Do NOT repeat the same template.
"""

    full_prompt = f"<s>[INST] {system_prompt}\nStudent Question: {user_input} [/INST]"

    payload = {
        "inputs": full_prompt,
        "parameters": {
            "max_new_tokens": 200,
            "temperature": 0.8
        }
    }

    response = requests.post(API_URL, headers=headers, json=payload)
    result = response.json()

    if isinstance(result, list):
        text = result[0]["generated_text"]
        return text.split("[/INST]")[-1].strip()

    return "Could you please clarify your question?"

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

        # Show user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Emotion detection
        emotion = detect_emotion(user_input)

        # AI Response
        bot_reply = generate_response(user_input, emotion)

        # Lead priority
        lead_status = lead_temperature(emotion)

        # Show bot reply
        st.session_state.messages.append({"role": "assistant", "content": bot_reply})
        with st.chat_message("assistant"):
            st.markdown(bot_reply)
            st.info(f"Lead Priority: {lead_status}")

        # Save entire conversation
        data = {
            "name": st.session_state.name,
            "phone": st.session_state.phone,
            "conversation": st.session_state.messages,
            "last_emotion": emotion,
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
