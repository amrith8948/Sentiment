import streamlit as st
import requests
import json
import os
from datetime import datetime

# ==============================
# CONFIG
# ==============================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

TABLE_NAME = "admissions_chat"

# ==============================
# BROCHURE LOCKED DATA
# (REPLACE WITH EXACT BROCHURE DATA)
# ==============================

BROCHURE_KNOWLEDGE = """
INVISOR GLOBAL OFFICIAL COURSE DETAILS:

ACCA:
- Coaching Fee: ₹3,50,000 – ₹4,50,000
- Duration: 2–3 years (depending on exemptions)
- Structured mentoring and exam support included.

CMA:
- Coaching Fee: ₹2,50,000 – ₹3,50,000
- Duration: 1.5–2 years
- Levels: Foundation, Intermediate, Final.

Scholarship:
- Installment guidance available.
- Financial support discussion possible.

ONLY use the above information.
Do not add anything outside this.
"""

# ==============================
# SESSION STATE INIT
# ==============================

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "lead_tags" not in st.session_state:
    st.session_state.lead_tags = []

if "lead_score" not in st.session_state:
    st.session_state.lead_score = 0

if "student_name" not in st.session_state:
    st.session_state.student_name = None

if "phone_number" not in st.session_state:
    st.session_state.phone_number = None

if "scholarship_interest" not in st.session_state:
    st.session_state.scholarship_interest = False

# ==============================
# LEAD SCORING
# ==============================

def calculate_lead_type(score):
    if score >= 80:
        return "Hot"
    elif score >= 40:
        return "Warm"
    else:
        return "Cold"

# ==============================
# SAVE TO SUPABASE
# ==============================

def save_chat():

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
        "lead_tags": st.session_state.lead_tags,
        "lead_score": st.session_state.lead_score,
        "lead_type": calculate_lead_type(st.session_state.lead_score),
        "scholarship_interest": st.session_state.scholarship_interest
    }

    requests.post(url, headers=headers, json=data, timeout=10)

# ==============================
# AI RESPONSE (BROCHURE LOCKED)
# ==============================

def generate_ai_response(user_input):

    system_prompt = f"""
You are an academic counsellor at Invisor Global.

Use ONLY this brochure data:

{BROCHURE_KNOWLEDGE}

Rules:
- Do NOT invent numbers.
- Do NOT mention external websites.
- If information not available, say:
  "Our academic counsellor can guide you personally."
- Keep tone friendly, casual and encouraging.
- Response under 120 words.
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama-3.1-8b-instant",
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": 250
    }

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=data,
        timeout=15
    )

    if response.status_code != 200:
        return "Let me guide you properly. Could you clarify your question?"

    return response.json()["choices"][0]["message"]["content"]

# ==============================
# UI
# ==============================

st.title("Invisor Academic Counsellor")

if not st.session_state.student_name:
    name = st.text_input("Enter your name")
    phone = st.text_input("Enter your phone number")

    if st.button("Start Chat"):
        if name and phone:
            st.session_state.student_name = name
            st.session_state.phone_number = phone
            st.success("Welcome! How can I help you today?")
        else:
            st.warning("Please enter name and phone number.")
    st.stop()

# ==============================
# CHAT
# ==============================

user_input = st.text_input("Ask your question")

if user_input:

    st.session_state.chat_history.append(
        {"role": "user", "content": user_input}
    )

    lower_text = user_input.lower()

    # AUTO TAGGING
    if "acca" in lower_text and "ACCA interest" not in st.session_state.lead_tags:
        st.session_state.lead_tags.append("ACCA interest")
        st.session_state.lead_score += 40

    if "cma" in lower_text and "CMA interest" not in st.session_state.lead_tags:
        st.session_state.lead_tags.append("CMA interest")
        st.session_state.lead_score += 40

    # SCHOLARSHIP TRIGGER
    if any(word in lower_text for word in [
        "financial issue", "can't afford", "budget", "expensive"
    ]):
        st.session_state.scholarship_interest = True
        st.session_state.lead_score += 30

    bot_reply = generate_ai_response(user_input)

    st.session_state.chat_history.append(
        {"role": "assistant", "content": bot_reply}
    )

    st.write(bot_reply)

    save_chat()
