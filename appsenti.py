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
# OFFICIAL BROCHURE DATA (EDIT WITH REAL VALUES)
# =====================================

BROCHURE_DATA = {
    "ACCA": {
        "coaching_fee": "₹ 3,50,000 – 4,50,000 (as per brochure)",
        "exam_fee_note": "Exam fees are paid directly to ACCA UK as per their official structure.",
        "duration": "2 to 3 years depending on exemptions.",
        "degree_info": "ACCA qualification may provide academic progression options as per ACCA rules."
    },
    "CMA": {
        "coaching_fee": "₹ 2,50,000 – 3,50,000 (as per brochure)",
        "duration": "1.5 to 2 years.",
        "structure": "3 Levels – Foundation, Intermediate, Final."
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

    high_intent = ["fees", "admission", "join", "apply", "batch", "enroll"]
    medium_intent = ["salary", "scope", "placement", "career", "duration"]

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
# AI COUNSELLING RESPONSE (NO FACTS)
# =====================================

def generate_ai_response(groq_key):

    if not groq_key:
        return "AI service not configured."

    system_prompt = """
You are a senior Academic Counsellor at Invisor Global, Kerala.

Rules:
- Be encouraging.
- Be clear and structured.
- Do NOT generate fees or numbers.
- Do NOT invent partnerships or degrees.
- If factual info is needed, keep response general.
- Keep response under 120 words.
- Encourage student politely.
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
            return "Please allow me a moment. Let me clarify that for you."

        result = response.json()
        return result["choices"][0]["message"]["content"]

    except:
        return "I'm facing a technical issue. Please try again."

# =====================================
# SUPABASE SAVE
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

    except:
        st.warning("Database connection issue.")

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

    user_input = st.chat_input("Ask about ACCA / CMA / Fees / Admission...")

    if user_input:

        st.session_state.chat_history.append(
            {"role": "user", "content": user_input}
        )

        user_text = user_input.lower()

        # ===== CONTROLLED FACT RESPONSES =====

        if "fees" in user_text and "acca" in user_text:
            bot_reply = f"""
For ACCA at Invisor:

Coaching Fee: {BROCHURE_DATA['ACCA']['coaching_fee']}

{BROCHURE_DATA['ACCA']['exam_fee_note']}

Duration: {BROCHURE_DATA['ACCA']['duration']}

Would you like a stage-wise breakdown?
"""

        elif "fees" in user_text and "cma" in user_text:
            bot_reply = f"""
For CMA at Invisor:

Coaching Fee: {BROCHURE_DATA['CMA']['coaching_fee']}

Duration: {BROCHURE_DATA['CMA']['duration']}

Structure: {BROCHURE_DATA['CMA']['structure']}

Would you like guidance on eligibility?
"""

        elif "degree" in user_text and "acca" in user_text:
            bot_reply = BROCHURE_DATA["ACCA"]["degree_info"]

        else:
            bot_reply = generate_ai_response(GROQ_API_KEY)

        st.session_state.chat_history.append(
            {"role": "assistant", "content": bot_reply}
        )

        emotion = detect_emotion(user_input)
        score, lead_type = calculate_lead_score(
            st.session_state.chat_history,
            emotion
        )

        save_chat(emotion, score, lead_type)

        st.write("Lead Score:", score)
        st.write("Lead Type:", lead_type)

        st.rerun()
