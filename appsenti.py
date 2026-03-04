import streamlit as st
import requests
import json

# ==============================
# CONFIG
# ==============================
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

st.set_page_config(page_title="Kerala Career Guidance AI", page_icon="🎓")
st.title("🎓 Kerala Career Guidance AI")
st.caption("AI Academic Counsellor for ACCA | CA | CMA")

# ==============================
# SESSION STATE
# ==============================
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "student_name" not in st.session_state:
    st.session_state.student_name = ""

if "saved" not in st.session_state:
    st.session_state.saved = False

# ==============================
# NAME INPUT
# ==============================
if not st.session_state.student_name:
    name = st.text_input("Enter your name to begin")
    if st.button("Start Chat"):
        if name.strip():
            st.session_state.student_name = name.strip()
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

        if isinstance(result, list):
            scores = result[0]
            top = max(scores, key=lambda x: x["score"])
            return top["label"]

        return "neutral"

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
You are a senior academic counsellor based in Kerala.

Student emotion detected: {emotion}

Your mission:
- Respond naturally like a human mentor
- Promote ACCA, CA, CMA smartly
- Adapt tone based on emotion
- Avoid repeating templates
- Keep under 150 words
- Ask 1 strong follow-up question
"""

    messages = [{"role": "system", "content": system_prompt}]

    # Add last 6 messages for context
    for msg in st.session_state.chat_history[-6:]:
        messages.append(msg)

    messages.append({"role": "user", "content": user_input})

    payload = {
        "model": "llama3-8b-8192",
        "messages": messages,
        "temperature": 1.0,
        "top_p": 0.95,
        "max_tokens": 250
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)

        if response.status_code != 200:
            return f"⚠ API ERROR {response.status_code}: {response.text}"

        result = response.json()

        if "choices" in result:
            return result["choices"][0]["message"]["content"]

        return "Could you tell me more about your goals?"

    except Exception as e:
        return f"Exception: {str(e)}"

# ==============================
# SAVE TO SUPABASE (ONE ROW)
# ==============================
def save_chat(final_emotion):

    if st.session_state.saved:
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
        st.session_state.saved = True
    except:
        pass

# ==============================
# DISPLAY CHAT
# ==============================
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# ==============================
# USER INPUT
# ==============================
user_input = st.chat_input("Type your message here...")

if user_input:

    emotion = detect_emotion(user_input)

    st.session_state.chat_history.append({
        "role": "user",
        "content": user_input
    })

    bot_reply = generate_response(user_input, emotion)

    st.session_state.chat_history.append({
        "role": "assistant",
        "content": bot_reply
    })

    save_chat(emotion)

    st.rerun()
