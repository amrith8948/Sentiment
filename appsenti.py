import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# -------------------------------
# CONFIG
# -------------------------------

HF_TOKEN = st.secrets["HF_TOKEN"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

MODEL = "j-hartmann/emotion-english-distilroberta-base"

# -------------------------------
# SUPABASE HEADERS
# -------------------------------

supabase_headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

# -------------------------------
# EMOTION DETECTION
# -------------------------------

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

# -------------------------------
# LEAD TEMPERATURE
# -------------------------------

def lead_temperature(emotion):
    if emotion in ["fear", "sadness"]:
        return "HOT 🔥"
    elif emotion == "joy":
        return "WARM 🌤"
    else:
        return "COLD ❄"

# -------------------------------
# BOT RESPONSE (KERALA FOCUSED)
# -------------------------------

def generate_response(emotion):

    closing = (
        "\n\n🎓 We offer:\n"
        "✔ Small Batch Personal Mentorship\n"
        "✔ Malayalam + English Support\n"
        "✔ First Attempt Strategy\n"
        "✔ Placement Guidance in Kerala & GCC\n\n"
        "Would you like to book a FREE 15-minute career guidance call?"
    )

    if emotion == "fear":
        return (
            "I understand career confusion is stressful.\n\n"
            "Many Kerala students after +2 feel unsure between ACCA, CA, or CMA.\n\n"
            "ACCA → Global career 🌍\n"
            "CA → Strong India recognition 🇮🇳\n"
            "CMA → Corporate finance growth 💼\n\n"
            "With the right mentorship, the path becomes clear."
            + closing
        )

    elif emotion == "sadness":
        return (
            "It sounds like you're feeling confused or low.\n\n"
            "Many successful students once felt the same.\n"
            "Proper mentorship changes everything."
            + closing
        )

    elif emotion == "anger":
        return (
            "I understand frustration — maybe due to lack of guidance.\n\n"
            "With structured preparation and mentor support, even tough courses become manageable."
            + closing
        )

    elif emotion == "joy":
        return (
            "That confidence is powerful! 🚀\n\n"
            "Professional courses like ACCA, CA, and CMA can multiply your career growth."
            + closing
        )

    else:
        return (
            "Are you currently after +2 or graduation?\n\n"
            "Finance professional courses open strong career paths."
            + closing
        )

# -------------------------------
# SAVE TO SUPABASE
# -------------------------------

def insert_chat(data):
    url = f"{SUPABASE_URL}/rest/v1/chats"
    response = requests.post(url, headers=supabase_headers, json=data)
    return response.status_code in [200, 201]

# -------------------------------
# UI
# -------------------------------

st.set_page_config(page_title="Kerala Academic Counsellor", layout="centered")

st.title("🎓 Kerala Career Guidance AI")
st.write("Chat with our Academic Counsellor for ACCA / CA / CMA")

name = st.text_input("Your Name")
phone = st.text_input("Phone Number")
message = st.text_area("Ask your career question")

if st.button("Send Message"):

    if name and phone and message:

        emotion = detect_emotion(message)
        bot_reply = generate_response(emotion)
        lead_status = lead_temperature(emotion)

        data = {
            "name": name,
            "phone": phone,
            "message": message,
            "emotion": emotion,
            "bot_reply": bot_reply,
            "lead_status": lead_status,
            "created_at": datetime.utcnow().isoformat()
        }

        success = insert_chat(data)

        if success:
            st.success("Message Sent ✅")
            st.write(f"### 🤖 Counsellor:")
            st.write(bot_reply)
            st.info(f"Lead Priority: {lead_status}")
            st.rerun()
        else:
            st.error("Error saving data")

    else:
        st.error("Please fill all fields")

# -------------------------------
# ADMIN PANEL
# -------------------------------

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
