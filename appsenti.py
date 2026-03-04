import streamlit as st
import requests
import json
import random

# ==============================
# CONFIG
# ==============================

SUPABASE_URL = "https://fxobfauvwlktyvvlhhot.supabase.co"
SUPABASE_KEY = "YOUR_SUPABASE_ANON_KEY"

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

st.set_page_config(page_title="Kerala Career Guidance AI")

# ==============================
# SESSION STATE
# ==============================

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "phone_number" not in st.session_state:
    st.session_state.phone_number = None

if "chat_completed" not in st.session_state:
    st.session_state.chat_completed = False


# ==============================
# LEAD SCORING
# ==============================

def calculate_lead_score(chat_history):
    score = 0

    high_intent = ["fees","admission","join","apply","duration",
                   "classes","scholarship","when start","how to join"]

    medium_intent = ["salary","scope","difficult","comparison",
                     "which better","career","job"]

    for msg in chat_history:
        if msg["role"] == "user":
            text = msg["content"].lower()

            for word in high_intent:
                if word in text:
                    score += 30

            for word in medium_intent:
                if word in text:
                    score += 10

    if score >= 70:
        return score, "Hot"
    elif score >= 40:
        return score, "Warm"
    else:
        return score, "Cold"


# ==============================
# SAVE TO SUPABASE (ONE ROW ONLY)
# ==============================

def save_chat(final_emotion):

    score, lead_type = calculate_lead_score(st.session_state.chat_history)

    url = f"{SUPABASE_URL}/rest/v1/admissions_chat?on_conflict=phone_number"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    data = {
        "phone_number": st.session_state.phone_number,
        "full_chat": st.session_state.chat_history,
        "last_emotion": final_emotion,
        "lead_score": score,
        "lead_type": lead_type
    }

    requests.post(url, headers=headers, json=data)


# ==============================
# EMOTION DETECTION (LIGHT)
# ==============================

def detect_emotion(text):
    text = text.lower()

    if any(x in text for x in ["confused","not sure","dont know"]):
        return "confused"
    if any(x in text for x in ["afraid","scared","fear"]):
        return "fear"
    if any(x in text for x in ["worried","tension"]):
        return "anxious"
    if any(x in text for x in ["excited","happy"]):
        return "excited"

    return "neutral"


# ==============================
# GROQ DYNAMIC RESPONSE
# ==============================

def generate_response(user_input, emotion):

    system_prompt = f"""
You are a highly intelligent academic counsellor targeting Kerala students.

Rules:
- Speak naturally (not robotic).
- Do NOT repeat same structure.
- Be conversational.
- Adapt reply based on student message.
- Soft sell ACCA / CA / CMA when relevant.
- Keep response under 120 words.
- Only close conversation when strong admission intent.
"""

    messages = [
        {"role": "system", "content": system_prompt}
    ]

    # Add full chat history for context
    for msg in st.session_state.chat_history:
        messages.append(msg)

    messages.append({"role": "user", "content": user_input})

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama-3.1-8b-instant",
        "messages": messages,
        "temperature": 0.9,
        "max_tokens": 300
    }

    response = requests.post(GROQ_URL, headers=headers, json=data)

    if response.status_code != 200:
        return "⚠ AI temporarily unavailable. Please try again."

    result = response.json()

    reply = result["choices"][0]["message"]["content"]

    return reply


# ==============================
# UI
# ==============================

st.title("🎓 Kerala Career Guidance AI")

# Step 1: Ask phone first
if not st.session_state.phone_number:
    phone = st.text_input("📞 Please share your number to continue:")

    if phone and len(phone) >= 10:
        st.session_state.phone_number = phone
        st.success("Thank you! Let's start.")
        st.rerun()

# Step 2: Chat
if st.session_state.phone_number:

    user_input = st.chat_input("Ask about ACCA, CA, CMA...")

    if user_input:

        st.session_state.chat_history.append(
            {"role": "user", "content": user_input}
        )

        emotion = detect_emotion(user_input)

        bot_reply = generate_response(user_input, emotion)

        score, lead_type = calculate_lead_score(
            st.session_state.chat_history
        )

        # Close only if HOT lead
        if score >= 70 and not st.session_state.chat_completed:
            bot_reply += "\n\nWe will give you a call to speak in person. Thank you"
            st.session_state.chat_completed = True
            save_chat(emotion)

        st.session_state.chat_history.append(
            {"role": "assistant", "content": bot_reply}
        )

        st.rerun()

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
