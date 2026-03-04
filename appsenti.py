import streamlit as st
import requests
import re
from datetime import datetime

# =====================================
# CONFIG
# =====================================

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

st.set_page_config(page_title="Invisor Academic Counsellor AI")

# =====================================
# SESSION STATE
# =====================================

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "phone_number" not in st.session_state:
    st.session_state.phone_number = None

if "chat_completed" not in st.session_state:
    st.session_state.chat_completed = False

if "course_interest" not in st.session_state:
    st.session_state.course_interest = "General"

# =====================================
# PHONE VALIDATION (INDIA)
# =====================================

def is_valid_phone(phone):
    pattern = r"^[6-9]\d{9}$"
    return re.match(pattern, phone)

# =====================================
# COURSE DETECTION
# =====================================

def detect_course_interest(text):
    text = text.lower()

    if "cma" in text:
        return "CMA USA"
    elif "acca" in text:
        return "ACCA + BCom"
    elif "fcp" in text or "internship" in text:
        return "First Career Program"
    elif "cpa" in text:
        return "CPA USA"
    elif "ea" in text:
        return "EA USA"
    else:
        return "General"

# =====================================
# EMOTION DETECTION
# =====================================

def detect_emotion(text):
    text = text.lower()

    if any(x in text for x in ["confused", "not sure"]):
        return "confused"
    if any(x in text for x in ["worried", "tension", "anxious"]):
        return "anxious"
    if any(x in text for x in ["fear", "scared"]):
        return "fear"
    if any(x in text for x in ["excited", "happy"]):
        return "excited"

    return "neutral"

# =====================================
# LEAD SCORING ENGINE
# =====================================

def calculate_lead_score(chat_history, emotion):

    score = 0

    high_intent = ["fees", "admission", "join", "apply", "batch", "when start"]
    medium_intent = ["salary", "scope", "career", "comparison", "placement"]

    for msg in chat_history:
        if msg["role"] == "user":
            text = msg["content"].lower()

            for word in high_intent:
                if word in text:
                    score += 40

            for word in medium_intent:
                if word in text:
                    score += 15

    if len(chat_history) >= 4:
        score += 10

    if emotion == "anxious":
        score += 10

    if score >= 80:
        return score, "Hot"
    elif score >= 40:
        return score, "Warm"
    else:
        return score, "Cold"

# =====================================
# SAVE TO SUPABASE
# =====================================

def save_chat(emotion, score, lead_type):

    url = f"{SUPABASE_URL}/rest/v1/admissions_chat?on_conflict=phone_number"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation"
    }

    data = {
        "phone_number": st.session_state.phone_number,
        "full_chat": st.session_state.chat_history,
        "last_emotion": emotion,
        "lead_score": score,
        "lead_type": lead_type,
        "course_interest": st.session_state.course_interest,
        "last_updated": datetime.now().isoformat()
    }

    response = requests.post(url, headers=headers, json=data)

    st.write("DEBUG STATUS:", response.status_code)
    st.write("DEBUG RESPONSE:", response.text)

    requests.post(url, headers=headers, json=data, timeout=15)

# =====================================
# GROQ RESPONSE GENERATOR
# =====================================

def generate_response(user_input):

    system_prompt = """
You are the official Academic Counsellor of Invisor Learning (Infopark Cochin).

About Invisor:
- Canadian-based finance consulting and offshore accounting firm.
- 600+ MNC placements.
- 92% admission-to-placement ratio.
- Offices in Cochin, Thrissur, and Canada.
- Offers CMA USA, ACCA + BCom, CPA USA, EA USA, and First Career Program (FCP).

Your Role:
- Guide students about CMA USA and ACCA programs.
- Explain duration, eligibility, curriculum, and career path clearly.
- Highlight Corporate Training Program (CTP) and FCP internship advantage when relevant.
- Emphasize real US accounting exposure and Infopark campus training.
- Speak professionally and confidently.
- Keep response under 140 words.
- Push for counselling call only if strong admission intent is shown.
"""

    messages = [{"role": "system", "content": system_prompt}]

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
        "temperature": 0.7,
        "max_tokens": 350
    }

    response = requests.post(GROQ_URL, headers=headers, json=data, timeout=20)

    if response.status_code != 200:
        return "⚠️ Our system is temporarily busy. Please try again."

    return response.json()["choices"][0]["message"]["content"]

# =====================================
# UI
# =====================================

st.title("🎓 Invisor Academic Counsellor AI")
st.caption("Infopark Cochin | Canada-Based Finance Training & Placement")

# STEP 1 - PHONE NUMBER
if not st.session_state.phone_number:

    phone = st.text_input("📞 Enter your 10-digit mobile number to continue:")

    if phone:
        if is_valid_phone(phone):
            st.session_state.phone_number = phone
            st.success("Verified ✅ You can now chat with our Academic Counsellor.")
            st.rerun()
        else:
            st.error("Please enter a valid Indian mobile number.")

# STEP 2 - CHAT
if st.session_state.phone_number:

    user_input = st.chat_input("Ask about CMA USA, ACCA, Placements, FCP...")

    if user_input:

        st.session_state.chat_history.append(
            {"role": "user", "content": user_input}
        )

        emotion = detect_emotion(user_input)
        st.session_state.course_interest = detect_course_interest(user_input)

        bot_reply = generate_response(user_input)

        score, lead_type = calculate_lead_score(
            st.session_state.chat_history, emotion
        )

        # Smart closing for HOT leads
        if score >= 80 and not st.session_state.chat_completed:
            bot_reply += "\n\nWould you like our academic team to call you for detailed guidance?"
            st.session_state.chat_completed = True

        st.session_state.chat_history.append(
            {"role": "assistant", "content": bot_reply}
        )

        save_chat(emotion, score, lead_type)

        st.rerun()

    # Display Chat
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
