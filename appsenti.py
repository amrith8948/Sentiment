import streamlit as st
import requests
import pandas as pd
from io import BytesIO

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="Emotion Chatbot", layout="centered")
st.title("Emotion-Aware AI Chatbot")

# -----------------------------
# LOAD SECRETS
# -----------------------------
HF_TOKEN = st.secrets["HF_TOKEN"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# -----------------------------
# EMOTION MODEL
# -----------------------------
MODEL_URL = "https://router.huggingface.co/hf-inference/models/j-hartmann/emotion-english-distilroberta-base"

hf_headers = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

def analyze_emotion(text):
    response = requests.post(
        MODEL_URL,
        headers=hf_headers,
        json={"inputs": text}
    )

    if response.status_code != 200:
        st.error(f"Model API Error: {response.status_code}")
        return None, None

    output = response.json()[0]
    best = sorted(output, key=lambda x: x["score"], reverse=True)[0]

    return best["label"].capitalize(), round(best["score"], 4)

# -----------------------------
# EMOTION BASED RESPONSE SYSTEM
# -----------------------------
def generate_response(emotion):
    responses = {
        "Joy": "I'm really happy to hear that! 😊 Tell me more about what's making you feel good.",
        "Sadness": "I'm sorry you're feeling this way. 💙 Do you want to talk about it?",
        "Anger": "It sounds like something upset you. 😡 What happened?",
        "Fear": "That sounds worrying. 😟 I'm here with you. What's on your mind?",
        "Disgust": "That must have felt uncomfortable. 😕 Want to share more?",
        "Neutral": "I see. Tell me more about that."
    }

    return responses.get(emotion, "I'm here to listen. Tell me more.")

# -----------------------------
# SUPABASE CONFIG
# -----------------------------
supabase_headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

def insert_chat(data):
    url = f"{SUPABASE_URL}/rest/v1/chats"

    response = requests.post(
        url,
        headers=supabase_headers,
        json=data
    )

    if response.status_code not in [200, 201]:
        st.error(f"Supabase Insert Error: {response.status_code}")
        st.write(response.text)

def fetch_chats():
    url = f"{SUPABASE_URL}/rest/v1/chats?select=*"

    response = requests.get(
        url,
        headers=supabase_headers
    )

    if response.status_code != 200:
        st.error(f"Supabase Fetch Error: {response.status_code}")
        return pd.DataFrame()

    return pd.DataFrame(response.json())

# -----------------------------
# SESSION CHAT HISTORY
# -----------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# -----------------------------
# CHAT INTERFACE
# -----------------------------
user_input = st.chat_input("Type your message...")

if user_input:

    emotion, confidence = analyze_emotion(user_input)

    if emotion:
        bot_reply = generate_response(emotion)

        # Store in session
        st.session_state.chat_history.append(("You", user_input))
        st.session_state.chat_history.append(("Bot", bot_reply))

        # Save to database
        insert_chat({
            "user_message": user_input,
            "detected_emotion": emotion,
            "confidence": confidence,
            "bot_response": bot_reply
        })

# Display chat history
for speaker, message in st.session_state.chat_history:
    with st.chat_message("user" if speaker == "You" else "assistant"):
        st.write(message)

# -----------------------------
# ADMIN SECTION
# -----------------------------
st.markdown("---")
st.subheader("Admin Access")

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:

    if st.checkbox("Login as Admin"):
        pin = st.text_input("Enter 4-digit PIN", type="password")

        if st.button("Login"):
            if pin == "8948":
                st.session_state.admin_logged_in = True
                st.rerun()
            else:
                st.error("Incorrect PIN")

# -----------------------------
# ADMIN DASHBOARD
# -----------------------------
if st.session_state.admin_logged_in:

    st.markdown("---")
    st.subheader("Chat Logs")

    df = fetch_chats()

    if not df.empty:
        st.dataframe(df, use_container_width=True)

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)

        output.seek(0)

        st.download_button(
            label="Download Chat History",
            data=output,
            file_name="chat_history.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    else:
        st.info("No chat data available.")

    if st.button("Logout Admin"):
        st.session_state.admin_logged_in = False
        st.rerun()
