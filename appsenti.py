import streamlit as st
import requests
import re
from datetime import datetime

# ==============================
# CONFIGURATION
# ==============================

SUPABASE_URL = "https://fxobfauvwlktyvvlhhot.supabase.co"
SUPABASE_KEY = "sb_publishable_cnKAbv00i67Y0sv8iAIzVg_1r-0tR5l"

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

if "chat_completed" not in st.session_state:
    st.session_state.chat_completed = False

# ==============================
# VALIDATION
# ==============================

def is_valid_phone(phone):
    return re.match(r"^[6-9]\d{9}$", phone)

# ==============================
# EMOTION DETECTION
# ==============================

def detect_emotion(text):
    text = text.lower()

    if any(x in text for x in ["confused", "not sure", "doubt"]):
        return "confused"
    if any(x in text for x in ["worried", "tension", "scared"]):
        return "anxious"
    if any(x in text for x in ["excited", "interested", "happy"]):
        return "excited"

    return "neutral"

# ==============================
# LEAD SCORING (FIXED)
# ==============================

def calculate_lead_score(chat_history, emotion):

    score = 0

    high_intent = [
        "fees", "admission", "join", "apply",
        "batch", "when start", "enroll", "register"
    ]

    medium_intent = [
        "salary", "scope", "placement",
        "career", "duration", "difficult"
    ]

    for msg in chat_history:
        if msg["role"] == "user":
            text = msg["content"].lower()

            for word in high_intent:
                if word in text:
                    score += 40

            for word in medium_intent:
                if word in text:
                    score += 15

    # Engagement bonus
    if len(chat_history) >= 6:
        score += 20

    # Emotional bonus
    if emotion == "anxious":
        score += 10

    # Classification (CORRECTED LOGIC)
    if score >= 80:
        lead_type = "Hot"
    elif score >= 40:
        lead_type = "Warm"
    else:
        lead_type = "Cold"

    return score, lead_type

# ==============================
# GROQ AI RESPONSE
# ==============================

def generate_ai_response():

    system_prompt = f"""
You are a professional Academic Counsellor from Invisor Global, Kerala.

About Invisor:
- Specializes in CMA (US), ACCA, CA coaching
- Expert faculty with industry experience
- Placement assistance support
- Flexible weekday and weekend batches
- Strong student mentoring

Rules:
- Speak naturally.
- Avoid robotic tone.
- Do not repeat same structure.
- Keep reply under 120 words.
- Adapt to student question.
- Softly promote course when relevant.
- If admission intent is strong, encourage counselling call.
"""

    messages = [{"role": "system", "content": system_prompt}]

    for msg in st.session_state.chat_history:
        messages.append(msg)

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama-3.1-8b-instant",
        "messages": messages,
        "temperature": 0.8,
        "max_tokens": 300
    }

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=15
        )

        if response.status_code != 200:
            return "I'm facing a small technical issue. Please try again."

        result = response.json()
        return result["choices"][0]["message"]["content"]

    except requests.exceptions.RequestException:
        return "Unable to connect to AI service. Please try again."

# ==============================
# SAVE TO SUPABASE (SAFE)
# ==============================

def save_chat(emotion, score, lead_type):

    try:
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

        requests.post(url, headers=headers, json=data, timeout=10)

    except requests.exceptions.RequestException:
        st.warning("Database connection failed. Lead not saved.")

# ==============================
# UI
# ==============================

st.title("🎓 Invisor Academic Counsellor")

# STEP 1 – PHONE
if not st.session_state.phone_number:

    phone = st.text_input("📞 Enter your 10-digit mobile number")

    if phone and is_valid_phone(phone):
        st.session_state.phone_number = phone
        st.success("Mobile verified ✅")
        st.rerun()

# STEP 2 – NAME
elif not st.session_state.student_name:

    name = st.text_input("👤 Please enter your full name")

    if name and len(name) > 2:
        st.session_state.student_name = name
        st.success(f"Welcome {name}! You can now chat.")
        st.rerun()

# STEP 3 – CHAT
else:

    st.success(f"Hello {st.session_state.student_name} 👋")

    # Display previous messages
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Ask about CMA / ACCA / CA / Fees / Admission...")

    if user_input:

        # Add user message
        st.session_state.chat_history.append(
            {"role": "user", "content": user_input}
        )

        # Detect emotion
        emotion = detect_emotion(user_input)

        # Generate AI response
        bot_reply = generate_ai_response()

        # Add AI response
        st.session_state.chat_history.append(
            {"role": "assistant", "content": bot_reply}
        )

        # Calculate lead score
        score, lead_type = calculate_lead_score(
            st.session_state.chat_history,
            emotion
        )

        # Strong push for HOT lead
        if score >= 80 and not st.session_state.chat_completed:
            st.session_state.chat_completed = True
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": "Would you like me to arrange a personal counselling call for admission guidance?"
                }
            )

        # Save to Supabase
        save_chat(emotion, score, lead_type)

        # Debug info (remove in production)
        st.write("Lead Score:", score)
        st.write("Lead Type:", lead_type)

        st.rerun()
