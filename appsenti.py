import streamlit as st
import requests
import json

# =====================================
# CONFIG
# =====================================

SUPABASE_URL = "https://fxobfauvwlktyvvlhhot.supabase.co"
SUPABASE_KEY = "YOUR_SUPABASE_ANON_KEY"  # <-- PUT YOUR REAL KEY HERE

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

st.set_page_config(page_title="Kerala Career Guidance AI")

# =====================================
# SESSION STATE
# =====================================

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "phone_number" not in st.session_state:
    st.session_state.phone_number = None

if "chat_completed" not in st.session_state:
    st.session_state.chat_completed = False

# =====================================
# LEAD SCORING
# =====================================

def calculate_lead_score(chat_history):
    score = 0

    high_intent = [
        "fees", "admission", "join", "apply",
        "duration", "scholarship", "when start",
        "how to join", "batch", "timing"
    ]

    medium_intent = [
        "salary", "scope", "difficult",
        "comparison", "which better", "career"
    ]

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

# =====================================
# SAVE TO SUPABASE (UPSERT)
# =====================================

def save_chat(final_emotion):

    score, lead_type = calculate_lead_score(st.session_state.chat_history)

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
        "last_emotion": final_emotion,
        "lead_score": score,
        "lead_type": lead_type
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code not in [200, 201]:
        st.error(f"❌ Supabase Error {response.status_code}")
        st.error(response.text)
    else:
        st.success("✅ Lead saved/updated in Supabase")

# =====================================
# SIMPLE EMOTION DETECTION
# =====================================

def detect_emotion(text):
    text = text.lower()

    if any(x in text for x in ["confused", "not sure"]):
        return "confused"
    if any(x in text for x in ["fear", "scared"]):
        return "fear"
    if any(x in text for x in ["worried", "tension"]):
        return "anxious"
    if any(x in text for x in ["excited", "happy"]):
        return "excited"

    return "neutral"

# =====================================
# GROQ RESPONSE GENERATOR
# =====================================

def generate_response(user_input):

    system_prompt = """
You are a smart, friendly academic counsellor targeting Kerala students.

Rules:
- Speak naturally (not robotic).
- Keep it conversational.
- Do NOT repeat same structure.
- Adapt to student question.
- Softly promote ACCA / CA / CMA when relevant.
- Keep reply under 120 words.
- Only push strongly if admission intent is clear.
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

    response = requests.post(GROQ_URL, headers=headers, json=data)

    if response.status_code != 200:
        return f"⚠ API ERROR {response.status_code}: {response.text}"

    result = response.json()

    return result["choices"][0]["message"]["content"]

# =====================================
# UI
# =====================================

st.title("🎓 Kerala Career Guidance AI")

# Step 1: Ask Phone Number
if not st.session_state.phone_number:

    phone = st.text_input("📞 Please share your number to continue:")

    if phone and len(phone) >= 10:
        st.session_state.phone_number = phone
        st.success("Thank you! You can now chat.")
        st.rerun()

# Step 2: Chat Interface
if st.session_state.phone_number:

    user_input = st.chat_input("Ask about ACCA, CA, CMA...")

    if user_input:

        # Save user message
        st.session_state.chat_history.append(
            {"role": "user", "content": user_input}
        )

        emotion = detect_emotion(user_input)

        bot_reply = generate_response(user_input)

        score, lead_type = calculate_lead_score(
            st.session_state.chat_history
        )

        # Only close if HOT lead
        if score >= 70 and not st.session_state.chat_completed:
            bot_reply += "\n\nWe will give you a call to speak in person. Thank you"
            st.session_state.chat_completed = True
            save_chat(emotion)

        st.session_state.chat_history.append(
            {"role": "assistant", "content": bot_reply}
        )

        st.rerun()

    # Display Chat
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
