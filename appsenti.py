import streamlit as st
import requests
import re
from datetime import datetime

# =====================================
# SAFE CONFIG
# =====================================

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    SUPABASE_URL = ""
    SUPABASE_KEY = ""
    GROQ_API_KEY = ""

TABLE_NAME = "admissions_chat"

st.set_page_config(page_title="Invisor Academic Counsellor")

# =====================================
# BROCHURE CONTROLLED DATA (EDIT EXACTLY)
# =====================================

BROCHURE_DATA = {
    "ACCA": {
        "coaching_fee": "₹ 3.5L – 4.5L (as per brochure)",
        "duration": "2–3 years depending on exemptions"
    },
    "CMA": {
        "coaching_fee": "₹ 2.5L – 3.5L (as per brochure)",
        "duration": "1.5–2 years"
    }
}

# =====================================
# SESSION STATE
# =====================================

if "phone_number" not in st.session_state:
    st.session_state.phone_number = None

if "student_name" not in st.session_state:
    st.session_state.student_name = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "lead_tags" not in st.session_state:
    st.session_state.lead_tags = []

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
    if any(x in text for x in ["worried", "scared", "tension"]):
        return "anxious"
    return "neutral"

# =====================================
# AUTO TAGGING
# =====================================

def detect_tags(user_input, existing_tags):
    text = user_input.lower()

    if "acca" in text and "ACCA_Interest" not in existing_tags:
        existing_tags.append("ACCA_Interest")

    if "cma" in text and "CMA_Interest" not in existing_tags:
        existing_tags.append("CMA_Interest")

    if "ca" in text and "CA_Interest" not in existing_tags:
        existing_tags.append("CA_Interest")

    financial_words = [
        "financial issue", "costly", "expensive",
        "fees high", "can't afford", "budget"
    ]

    if any(word in text for word in financial_words):
        if "Scholarship_Concern" not in existing_tags:
            existing_tags.append("Scholarship_Concern")

    return existing_tags

# =====================================
# LEAD SCORING
# =====================================

def calculate_lead_score(chat_history):

    score = 0

    high_intent = ["fees", "admission", "join", "apply", "when start"]
    medium_intent = ["salary", "scope", "career", "duration"]

    for msg in chat_history:
        if msg["role"] == "user":
            text = msg["content"].lower()

            for word in high_intent:
                if word in text:
                    score += 40

            for word in medium_intent:
                if word in text:
                    score += 15

    if score >= 80:
        return score, "Hot"
    elif score >= 40:
        return score, "Warm"
    else:
        return score, "Cold"

# =====================================
# AI RESPONSE (NO FACT GENERATION)
# =====================================

def generate_ai_response():

    system_prompt = """
You are a professional academic counsellor at Invisor Global.

Rules:
- Be encouraging.
- Be clear.
- Do NOT invent fees.
- Do NOT invent partnerships.
- Keep response under 120 words.
"""

    messages = [{"role": "system", "content": system_prompt}]
    messages += st.session_state.chat_history

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama-3.1-8b-instant",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 250
    }

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=15
        )

        if response.status_code != 200:
            return "Let me clarify that for you."

        return response.json()["choices"][0]["message"]["content"]

    except:
        return "Facing a small technical issue."

# =====================================
# SAVE TO SUPABASE
# =====================================

def save_chat(emotion, score, lead_type):

    if not SUPABASE_URL:
        return

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
        "lead_tags": st.session_state.lead_tags,
        "last_updated": datetime.utcnow().isoformat()
    }

    requests.post(url, headers=headers, json=data)

# =====================================
# UI
# =====================================

st.title("🎓 Invisor Academic Counsellor")

# PHONE
if not st.session_state.phone_number:
    phone = st.text_input("📞 Enter mobile number")
    if phone and is_valid_phone(phone):
        st.session_state.phone_number = phone
        st.rerun()

# NAME
elif not st.session_state.student_name:
    name = st.text_input("👤 Enter full name")
    if name:
        st.session_state.student_name = name
        st.rerun()

# CHAT
else:

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Ask about ACCA / CMA / Fees...")

    if user_input:

        st.session_state.chat_history.append(
            {"role": "user", "content": user_input}
        )

        st.session_state.lead_tags = detect_tags(
            user_input,
            st.session_state.lead_tags
        )

        user_text = user_input.lower()

        # Controlled responses
        if "fees" in user_text and "acca" in user_text:
            bot_reply = f"""
ACCA Coaching Fee: {BROCHURE_DATA['ACCA']['coaching_fee']}
Duration: {BROCHURE_DATA['ACCA']['duration']}
"""

        elif "fees" in user_text and "cma" in user_text:
            bot_reply = f"""
CMA Coaching Fee: {BROCHURE_DATA['CMA']['coaching_fee']}
Duration: {BROCHURE_DATA['CMA']['duration']}
"""

        elif "financial issue" in user_text or "can't afford" in user_text:
            bot_reply = """
I understand your concern. We do provide structured payment options and scholarship guidance.

Would you like me to connect you with our academic counsellor for financial planning support?
"""

        else:
            bot_reply = generate_ai_response()

        st.session_state.chat_history.append(
            {"role": "assistant", "content": bot_reply}
        )

        emotion = detect_emotion(user_input)
        score, lead_type = calculate_lead_score(
            st.session_state.chat_history
        )

        save_chat(emotion, score, lead_type)

        st.write("Lead Score:", score)
        st.write("Lead Type:", lead_type)
        st.write("Tags:", st.session_state.lead_tags)

        st.rerun()
