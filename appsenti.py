import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# ---------------- CONFIG ---------------- #

HF_TOKEN = st.secrets["HF_TOKEN"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

MODEL = "j-hartmann/emotion-english-distilroberta-base"

supabase_headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

# ---------------- EMOTION DETECTION ---------------- #

def detect_emotion(text):
    API_URL = f"https://router.huggingface.co/hf-inference/models/{MODEL}"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {"inputs": text}

    response = requests.post(API_URL, headers=headers, json=payload)
    result = response.json()

    if isinstance(result, list):
        emotions = result[0]
        top_emotion = max(emotions, key=lambda x: x['score'])
        return top_emotion['label']
    return "neutral"

# ---------------- LEAD TEMPERATURE ---------------- #

def lead_temperature(emotion):
    if emotion in ["fear", "sadness"]:
        return "HOT 🔥"
    elif emotion == "joy":
        return "WARM 🌤"
    else:
        return "COLD ❄"

# ---------------- BOT RESPONSE ---------------- #

def generate_response(emotion):

    closing = (
        "\n\n🎓 We offer:\n"
        "✔ Small Batch Mentorship\n"
        "✔ Malayalam + English Support\n"
        "✔ First Attempt Strategy\n"
        "✔ Kerala & GCC Placement Guidance\n\n"
        "Would you like to book a FREE career clarity call?"
    )

    if emotion == "fear":
        return (
            "I understand career confusion can be stressful.\n\n"
            "Many Kerala students feel unsure between ACCA, CA, or CMA.\n\n"
            "ACCA → Global 🌍\n"
            "CA → Strong India 🇮🇳\n"
            "CMA → Corporate 💼\n\n"
            "With right guidance, it becomes clear."
            + closing
        )

    elif emotion == "sadness":
        return (
            "It sounds like you're feeling confused.\n\n"
            "Many successful students once felt the same.\n"
            "Proper mentorship changes everything."
            + closing
        )

    elif emotion == "anger":
        return (
            "I understand frustration due to lack of guidance.\n\n"
            "With structured mentorship, even tough courses become manageable."
            + closing
        )

    elif emotion == "joy":
        return (
            "That confidence is powerful! 🚀\n\n"
            "Professional courses can multiply your growth."
            + closing
        )

    else:
        return (
            "Are you after +2 or graduation?\n\n"
            "Finance professional courses open strong career paths."
            + closing
        )

# ---------------- SUPABASE SAVE ---------------- #

def insert_chat(data):
    url = f"{SUPABASE_URL}/rest/v1/chats"
    response = requests.post(url, headers=supabase_headers, json=data)
    return response.status_code in [200, 201]

# ---------------- STREAMLIT UI ---------------- #

st.set_page_config(page_title="Kerala Academic Counsellor", layout="centered")
st.title("🎓 Kerala Career Guidance AI")

# Session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Ask user info once
if "user_info_collected" not in st.session_state:
    st.session_state.user_info_collected = False

if not st.session_state.user_info_collected:
    with st.form("lead_form"):
        name = st.text_input("Your Name")
        phone = st.text_input("Phone Number")
        submitted = st.form_submit_button("Start Chat")

        if submitted:
            if name and phone:
                st.session_state.name = name
                st.session_state.phone = phone
                st.session_state.user_info_collected = True
                st.rerun()
            else:
                st.error("Please enter name and phone")

# ---------------- CHAT INTERFACE ---------------- #

if st.session_state.user_info_collected:

    # Display previous messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    user_input = st.chat_input("Ask your career question...")

    if user_input:

        # Show user message
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("user"):
            st.markdown(user_input)

        # Detect emotion
        emotion = detect_emotion(user_input)

        # Generate response
        bot_reply = generate_response(emotion)
        lead_status = lead_temperature(emotion)

        # Show bot reply
        st.session_state.messages.append({"role": "assistant", "content": bot_reply})

        with st.chat_message("assistant"):
            st.markdown(bot_reply)
            st.info(f"Lead Priority: {lead_status}")

        # Save to Supabase
        data = {
            "name": st.session_state.name,
            "phone": st.session_state.phone,
            "message": user_input,
            "emotion": emotion,
            "bot_reply": bot_reply,
            "lead_status": lead_status,
            "created_at": datetime.utcnow().isoformat()
        }

        insert_chat(data)

# ---------------- ADMIN PANEL ---------------- #

st.markdown("---")
admin = st.checkbox("Admin Login")

if admin:
    pin = st.text_input("Enter 4-digit PIN", type="password")

    if pin == "8948":

        st.subheader("📊 Admissions Data")

        url = f"{SUPABASE_URL}/rest/v1/chats?select=*"
        response = requests.get(url, headers=supabase_headers)

        if response.status_code == 200:
            df = pd.DataFrame(response.json())
            st.dataframe(df)
        else:
            st.error("Failed to fetch data")
