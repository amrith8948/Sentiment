import streamlit as st
import requests
import re
import json

# ==============================
# CONFIG
# ==============================
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

st.set_page_config(page_title="Kerala Career Guidance AI", page_icon="🎓")
st.title("🎓 Kerala Career Guidance AI")

# ==============================
# SESSION STATE
# ==============================
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "student_name" not in st.session_state:
    st.session_state.student_name = ""

if "phone_number" not in st.session_state:
    st.session_state.phone_number = None

# ==============================
# NAME INPUT
# ==============================
if not st.session_state.student_name:
    name = st.text_input("Enter your name")
    if st.button("Start Chat"):
        if name.strip():
            st.session_state.student_name = name.strip()
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": "Hi 👋 Please share your mobile number so we can guide you better."
            })
            st.rerun()
    st.stop()

# ==============================
# EMOTION DETECTION
# ==============================
def detect_emotion(text):
    try:
        url = "https://api-inference.huggingface.co/models/SamLowe/roberta-base-go_emotions"
        response = requests.post(url, json={"inputs": text}, timeout=10)

        if response.status_code != 200:
            return "neutral"

        result = response.json()
        scores = result[0]
        top = max(scores, key=lambda x: x["score"])
        return top["label"]

    except:
        return "neutral"

# ==============================
# GROQ RESPONSE (Natural Flow)
# ==============================
def generate_response(user_input, emotion):

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    system_prompt = f"""
You are a friendly academic counsellor from Kerala.

Student emotion: {emotion}

Talk naturally like WhatsApp.
Guide towards ACCA, CA, CMA intelligently.
Do NOT end every message with a fixed closing line.
Ask only one relevant question.
Keep it conversational and human.
"""

    messages = [{"role": "system", "content": system_prompt}]

    for msg in st.session_state.chat_history[-8:]:
        messages.append(msg)

    messages.append({"role": "user", "content": user_input})

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 1.1,
        "max_tokens": 200
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        return "Could you tell me more about your career goals?"

    result = response.json()
    return result["choices"][0]["message"]["content"]

# ==============================
# UPSERT TO SUPABASE (ONE ROW)
# ==============================
def save_chat(final_emotion):

    url = f"{SUPABASE_URL}/rest/v1/admissions_chat?on_conflict=phone_number"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    data = {
        "student_name": st.session_state.student_name,
        "phone_number": st.session_state.phone_number,
        "full_chat": st.session_state.chat_history,
        "last_emotion": final_emotion
    }

    requests.post(url, headers=headers, json=data)

# ==============================
# DISPLAY CHAT
# ==============================
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# ==============================
# USER INPUT
# ==============================
user_input = st.chat_input("Type your message")

if user_input:

    st.session_state.chat_history.append({
        "role": "user",
        "content": user_input
    })

    # Capture phone first
    if not st.session_state.phone_number:
        if re.fullmatch(r"[6-9]\d{9}", user_input.strip()):
            st.session_state.phone_number = user_input.strip()
            reply = "Thanks 👍 How can I guide you regarding ACCA, CA or CMA?"
        else:
            reply = "Please enter a valid 10-digit Kerala mobile number."

        st.session_state.chat_history.append({
            "role": "assistant",
            "content": reply
        })

        st.rerun()

    # After number captured
    emotion = detect_emotion(user_input)
    bot_reply = generate_response(user_input, emotion)

    st.session_state.chat_history.append({
        "role": "assistant",
        "content": bot_reply
    })

    save_chat(emotion)

    st.rerun()
