import streamlit as st
import requests
import json
from datetime import datetime

# -------------------------------
# CONFIG
# -------------------------------
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# -------------------------------
# PAGE SETTINGS
# -------------------------------
st.set_page_config(page_title="Kerala Career Guidance AI", page_icon="🎓")
st.title("🎓 Kerala Career Guidance AI")
st.caption("AI Academic Counsellor for ACCA | CA | CMA")

# -------------------------------
# SESSION STATE
# -------------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "student_name" not in st.session_state:
    st.session_state.student_name = ""

if "session_saved" not in st.session_state:
    st.session_state.session_saved = False

# -------------------------------
# NAME INPUT (FIRST STEP)
# -------------------------------
if not st.session_state.student_name:
    name = st.text_input("Enter your name")
    if st.button("Start Chat"):
        if name.strip():
            st.session_state.student_name = name
            st.rerun()
    st.stop()

# -------------------------------
# EMOTION DETECTION (HF FREE API)
# -------------------------------
def detect_emotion(text):
    url = "https://api-inference.huggingface.co/models/SamLowe/roberta-base-go_emotions"
    headers = {"Content-Type": "application/json"}

    payload = {"inputs": text}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)

        if response.status_code != 200:
            return "neutral"

        result = response.json()

        if isinstance(result, list):
            scores = result[0]
            top = max(scores, key=lambda x: x["score"])
            return top["label"]

        return "neutral"

    except:
        return "neutral"

# -------------------------------
# GROQ RESPONSE GENERATION
# -------------------------------
def generate_response(user_input, emotion):

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    system_prompt = f"""
You are a highly trained academic counsellor from Kerala.

Student emotion: {emotion}

Instructions:
- Speak naturally like a Kerala mentor
- Adapt tone based on emotion
- Promote ACCA, CA, CMA smartly
- DO NOT repeat same reply
- Keep under 150 words
- Ask one engaging follow-up question
- Be persuasive but not pushy
"""

    # Include chat memory
    messages = [
        {"role": "system", "content": system_prompt.strip()}
    ]

    for msg in st.session_state.chat_history[-6:]:
        messages.append(msg)

    messages.append({"role": "user", "content": user_input.strip()})

    payload = {
        "model": "llama3-70b-8192",
        "messages": messages,
        "temperature": 0.9,
        "top_p": 0.9,
        "max_tokens": 250
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)

        if response.status_code != 200:
            return "That’s interesting. Tell me more about your career goals."

        result = response.json()

        return result["choices"][0]["message"]["content"]

    except:
        return "I’d love to guide you properly. What are you currently studying?"

# -------------------------------
# SAVE TO SUPABASE (ONE ROW PER CHAT)
# -------------------------------
def save_chat_to_supabase(final_emotion):

    if st.session_state.session_saved:
        return

    url = f"{SUPABASE_URL}/rest/v1/admissions_chat"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }

    data = {
        "student_name": st.session_state.student_name,
        "full_chat": st.session_state.chat_history,
        "last_emotion": final_emotion
    }

    try:
        requests.post(url, headers=headers, json=data)
        st.session_state.session_saved = True
    except:
        pass

# -------------------------------
# CHAT DISPLAY
# -------------------------------
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# -------------------------------
# USER INPUT
# -------------------------------
user_input = st.chat_input("Type your message here...")

if user_input:

    # Detect emotion
    emotion = detect_emotion(user_input)

    # Save user message
    st.session_state.chat_history.append({
        "role": "user",
        "content": user_input
    })

    # Generate AI reply
    bot_reply = generate_response(user_input, emotion)

    st.session_state.chat_history.append({
        "role": "assistant",
        "content": bot_reply
    })

    # Save session to Supabase
    save_chat_to_supabase(emotion)

    st.rerun()
