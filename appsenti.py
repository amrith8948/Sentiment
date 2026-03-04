import streamlit as st
import requests
import json
import random

# -----------------------------
# CONFIG
# -----------------------------

SUPABASE_URL = "https://fxobfauvwlktyvvlhhot.supabase.co"
SUPABASE_KEY = "YOUR_SUPABASE_ANON_KEY"

st.set_page_config(page_title="Kerala Career Guidance AI")

# -----------------------------
# SESSION INIT
# -----------------------------

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "phone_number" not in st.session_state:
    st.session_state.phone_number = None

if "student_name" not in st.session_state:
    st.session_state.student_name = None

if "chat_completed" not in st.session_state:
    st.session_state.chat_completed = False

# -----------------------------
# LEAD SCORING
# -----------------------------

def calculate_lead_score(chat_history):
    score = 0
    
    high_intent = [
        "fees", "admission", "join", "apply",
        "duration", "classes start", "eligibility", "scholarship"
    ]

    medium_intent = [
        "salary", "scope", "difficulty",
        "comparison", "which is better", "career"
    ]

    low_intent = [
        "what is", "just checking", "not sure", "thinking"
    ]

    for msg in chat_history:
        if msg["role"] == "user":
            text = msg["content"].lower()

            for word in high_intent:
                if word in text:
                    score += 25

            for word in medium_intent:
                if word in text:
                    score += 10

            for word in low_intent:
                if word in text:
                    score += 3

    if score >= 70:
        lead_type = "Hot"
    elif score >= 40:
        lead_type = "Warm"
    else:
        lead_type = "Cold"

    return score, lead_type

# -----------------------------
# SAVE TO SUPABASE
# -----------------------------

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
        "student_name": st.session_state.student_name,
        "phone_number": st.session_state.phone_number,
        "full_chat": st.session_state.chat_history,
        "last_emotion": final_emotion,
        "lead_score": score,
        "lead_type": lead_type
    }

    requests.post(url, headers=headers, json=data)

# -----------------------------
# EMOTION DETECTION (Simple)
# -----------------------------

def detect_emotion(text):
    text = text.lower()

    if any(x in text for x in ["confused", "not sure", "dont know"]):
        return "confused"
    if any(x in text for x in ["afraid", "fear", "scared"]):
        return "fear"
    if any(x in text for x in ["sad", "worried"]):
        return "sad"
    if any(x in text for x in ["happy", "excited"]):
        return "happy"

    return "neutral"

# -----------------------------
# DYNAMIC RESPONSE GENERATOR
# -----------------------------

def generate_response(user_input, emotion):

    openings = {
        "confused": "I understand you're confused.",
        "fear": "It's completely normal to feel that way.",
        "sad": "Don't worry, many students feel this initially.",
        "happy": "That's great to hear!",
        "neutral": "That's a good question."
    }

    intro = openings.get(emotion, "I understand.")

    dynamic_closings = [
        "Would you like details about fees or eligibility?",
        "Shall I explain duration and exam structure?",
        "Would you like to know placement support details?",
        "Shall I share scholarship information?"
    ]

    closing = random.choice(dynamic_closings)

    main_content = f"""
{intro}

In Kerala, many students after +2 choose professional courses like ACCA, CA or CMA depending on their career goals.

• ACCA – Global recognition 🌍
• CA – Strong India reputation 🇮🇳
• CMA – Corporate finance focus 📊

{closing}
"""

    return main_content

# -----------------------------
# UI
# -----------------------------

st.title("🎓 Kerala Career Guidance AI")

# Step 1 – Ask Phone Number First
if not st.session_state.phone_number:
    phone = st.text_input("📞 Please share your number to continue:")

    if phone and len(phone) >= 10:
        st.session_state.phone_number = phone
        st.success("Thank you! You can now start chatting.")
        st.rerun()

# Step 2 – Chat Interface
if st.session_state.phone_number:

    user_input = st.chat_input("Type your message...")

    if user_input:

        # Save user message
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_input
        })

        emotion = detect_emotion(user_input)

        bot_reply = generate_response(user_input, emotion)

        # If high intent → close conversation
        score, lead_type = calculate_lead_score(st.session_state.chat_history)

        if score >= 70 and not st.session_state.chat_completed:
            bot_reply += "\n\nWe will give you a call to speak in person. Thank you"
            st.session_state.chat_completed = True
            save_chat(emotion)

        st.session_state.chat_history.append({
            "role": "assistant",
            "content": bot_reply
        })

        st.rerun()

    # Display Chat
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
