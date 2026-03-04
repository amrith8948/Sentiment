import streamlit as st
import requests
import re

# ==============================
# CONFIG
# ==============================
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

st.set_page_config(page_title="Kerala Career Guidance AI", page_icon="🎓")
st.title("🎓 Kerala Career Guidance AI")
st.caption("Academic Counsellor – ACCA | CA | CMA")

# ==============================
# SESSION STATE
# ==============================
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "student_name" not in st.session_state:
    st.session_state.student_name = ""

if "phone_number" not in st.session_state:
    st.session_state.phone_number = None

if "saved" not in st.session_state:
    st.session_state.saved = False

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
                "content": "Please share your number so we can guide you better."
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
# GROQ RESPONSE
# ==============================
def generate_response(user_input, emotion):

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    system_prompt = f"""
You are a Kerala-based academic counsellor.

Emotion detected: {emotion}

Speak naturally.
Guide towards ACCA, CA, CMA.
Keep it conversational.
Ask one engaging question.
Keep under 120 words.
End with:
We will give you a call to speak in person.Thank you
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 1.1,
        "max_tokens": 200
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        return "Our team will connect with you shortly. We will give you a call to speak in person.Thank you"

    result = response.json()
    return result["choices"][0]["message"]["content"]

# ==============================
# SAVE TO SUPABASE
# ==============================
def save_chat(final_emotion):

    url = f"{SUPABASE_URL}/rest/v1/admissions_chat"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
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

    # If phone not captured, validate number
    if not st.session_state.phone_number:
        if re.fullmatch(r"[6-9]\d{9}", user_input.strip()):
            st.session_state.phone_number = user_input.strip()
            reply = "Thank you for sharing your number. How can I help you regarding ACCA, CA or CMA?"
        else:
            reply = "Please enter a valid 10-digit mobile number starting with 6,7,8 or 9."

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
