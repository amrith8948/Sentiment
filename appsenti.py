import streamlit as st
import requests
import re
from datetime import datetime

# =====================================
# SAFE CONFIG (Works Local + Cloud)
# =====================================

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except Exception:
    SUPABASE_URL = ""
    SUPABASE_KEY = ""
    GROQ_API_KEY = ""

TABLE_NAME = "admissions_chat"

st.set_page_config(page_title="Invisor Academic Counsellor")

# =====================================
# SESSION STATE
# =====================================

if "phone_number" not in st.session_state:
    st.session_state.phone_number = None

if "student_name" not in st.session_state:
    st.session_state.student_name = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "chat_completed" not in st.session_state:
    st.session_state.chat_completed = False

# =====================================
# VALIDATION
# =====================================

def is_valid_phone(phone):
    return re.match(r"^[6-9]\d{9}$", phone)

# =====================================
# EMOTION DETECTION
# =====================================

def detect_emotion(text):
    text = text.lower()

    if any(x in text for x in ["confused", "not sure", "doubt"]):
        return "confused"
    if any(x in text for x in ["worried", "tension", "scared"]):
        return "anxious"
    if any(x in text for x in ["excited", "interested", "happy"]):
        return "excited"

    return "neutral"

# =====================================
# LEAD SCORING
# =====================================

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

    if len(chat_history) >= 6:
        score += 20

    if emotion == "anxious":
        score += 10

    if score >= 80:
        lead_type = "Hot"
    elif score >= 40:
        lead_type = "Warm"
    else:
        lead_type = "Cold"

    return score, lead_type

# =====================================
# AI RESPONSE GENERATOR
# =====================================

def generate_ai_response(groq_key):

    if not groq_key:
        return "AI service not configured properly."

    system_prompt = """
You are a senior Academic Counsellor from Invisor Global, Kerala.

Your tone:
- Confident
- Encouraging
- Clear
- Not robotic
- Not salesy
- Not pushy
- Not exaggerated

Important:
- NEVER inflate fee numbers.
- Give realistic Kerala market ranges.
- Break fees clearly (exam + coaching).
- Do not give extreme ranges like 8-12 lakhs.
- Keep answers reassuring and structured.
- Avoid long paragraphs.
- Keep reply under 120 words.
- Make student feel supported.

Invisor Focus:
- CMA (US)
- ACCA
- CA Foundation support
- Mentoring + placement assistance

If student asks about fees:
- Explain components clearly.
- Mention it is an investment in global qualification.
- Offer to explain roadmap.
- Avoid shocking numbers.

If student sounds confused:
- Reassure them.
- Guide step-by-step.

If admission intent is strong:
- Suggest personal counselling call politely.

Always adapt response to question.
"""
    messages = [{"role": "system", "content": system_prompt}]

    for msg in st.session_state.chat_history:
        messages.append(msg)

    headers = {
        "Authorization": f"Bearer {groq_key}",
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

# =====================================
# SAVE TO SUPABASE
# =====================================

def save_chat(emotion, score, lead_type):

    if not SUPABASE_URL or not SUPABASE_KEY:
        return

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

# =====================================
# UI
# =====================================

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

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Ask about CMA / ACCA / CA / Fees / Admission...")

    if user_input:

        st.session_state.chat_history.append(
            {"role": "user", "content": user_input}
        )

        emotion = detect_emotion(user_input)

        bot_reply = generate_ai_response(GROQ_API_KEY)

        st.session_state.chat_history.append(
            {"role": "assistant", "content": bot_reply}
        )

        score, lead_type = calculate_lead_score(
            st.session_state.chat_history,
            emotion
        )

        if score >= 80 and not st.session_state.chat_completed:
            st.session_state.chat_completed = True
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": "Would you like me to arrange a personal counselling call for admission guidance?"
                }
            )

        save_chat(emotion, score, lead_type)

        # Debug (remove later)
        st.write("Lead Score:", score)
        st.write("Lead Type:", lead_type)

        st.rerun()
