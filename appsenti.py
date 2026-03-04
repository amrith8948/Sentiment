import streamlit as st
import requests
import re
from datetime import datetime

# ==============================
# CONFIGURATION
# ==============================

SUPABASE_URL = "https://YOUR_PROJECT_ID.supabase.co"
SUPABASE_KEY = "YOUR_PUBLISHABLE_KEY"

TABLE_NAME = "admissions_chat"

st.set_page_config(page_title="Invisor Academic Counsellor", layout="centered")

# ==============================
# SESSION STATE
# ==============================

if "phone_number" not in st.session_state:
    st.session_state.phone_number = None

if "student_name" not in st.session_state:
    st.session_state.student_name = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ==============================
# UTILITIES
# ==============================

def is_valid_phone(phone):
    return re.match(r"^[6-9]\d{9}$", phone)

def detect_emotion(text):
    text = text.lower()
    if any(word in text for word in ["confused", "worried", "not sure", "scared"]):
        return "anxious"
    elif any(word in text for word in ["excited", "interested", "love"]):
        return "excited"
    return "neutral"

def calculate_lead_score(chat_history, emotion):

    score = 0

    high_intent = ["fees", "admission", "join", "apply", "batch", "when start"]
    medium_intent = ["salary", "scope", "career", "placement", "duration"]

    for msg in chat_history:
        if msg["role"] == "user":
            text = msg["content"].lower()

            for word in high_intent:
                if word in text:
                    score += 40

            for word in medium_intent:
                if word in text:
                    score += 15

    if len(chat_history) >= 6:
        score += 15

    if emotion == "anxious":
        score += 10

    if score >= 80:
        lead_type = "Hot"
    elif score >= 40:
        lead_type = "Warm"
    else:
        lead_type = "Cold"

    return score, lead_type

# ==============================
# SUPABASE SAVE
# ==============================

def save_chat(emotion, score, lead_type):

    url = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}?on_conflict=phone_number"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    data = {
        "phone_number": st.session_state.phone_number,
        "student_name": st.session_state.student_name,
        "full_chat": st.session_state.chat_history,
        "last_emotion": emotion,
        "lead_score": score,
        "lead_type": lead_type,
        "last_updated": datetime.utcnow().isoformat()
    }

    response = requests.post(url, headers=headers, json=data)

    print("STATUS:", response.status_code)
    print("RESPONSE:", response.text)

# ==============================
# UI
# ==============================

st.title("🎓 Invisor Academic Counsellor")

# STEP 1 – PHONE
if not st.session_state.phone_number:

    phone = st.text_input("📞 Enter your 10-digit mobile number:")

    if phone and is_valid_phone(phone):
        st.session_state.phone_number = phone
        st.success("Mobile verified ✅")
        st.rerun()

# STEP 2 – NAME
elif not st.session_state.student_name:

    name = st.text_input("👤 Please enter your full name:")

    if name and len(name) > 2:
        st.session_state.student_name = name
        st.success(f"Welcome {name}! You can now chat with our Academic Counsellor.")
        st.rerun()

# STEP 3 – CHAT
else:

    st.success(f"Hello {st.session_state.student_name} 👋")

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Ask about CMA / ACCA / Admissions / Fees...")

    if user_input:

        # Add user message
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_input
        })

        # Detect emotion
        emotion = detect_emotion(user_input)

        # Academic Counsellor Response
        response_text = f"""
Hi {st.session_state.student_name},

Thank you for your interest in Invisor Global.

Regarding your query about "{user_input}",

Our CMA and ACCA programs are designed with:
• Expert Faculty
• Placement Assistance
• Flexible Batches
• Industry-Focused Curriculum

Would you like details about fees, duration, or career scope?
"""

        st.session_state.chat_history.append({
            "role": "assistant",
            "content": response_text
        })

        # Calculate lead score
        score, lead_type = calculate_lead_score(
            st.session_state.chat_history,
            emotion
        )

        # Save to Supabase
        save_chat(emotion, score, lead_type)

        # Debug Display
        st.write("Lead Score:", score)
        st.write("Lead Type:", lead_type)

        st.rerun()
