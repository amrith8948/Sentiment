import streamlit as st
import requests
import pandas as pd
from io import BytesIO

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="Academic Counsellor AI", layout="centered")
st.title("🎓 AI Academic Counsellor")
st.markdown("Helping you choose the right professional course – ACCA | CA | CMA")

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
        return "Neutral", 0.0

    output = response.json()[0]
    best = sorted(output, key=lambda x: x["score"], reverse=True)[0]
    return best["label"].capitalize(), round(best["score"], 4)

# -----------------------------
# COUNSELLOR RESPONSE ENGINE
# -----------------------------
def generate_response(emotion, user_input):

    base_pitch = (
        "\n\nAt our institute, we provide:\n"
        "✔ Personal mentorship\n"
        "✔ Expert faculty\n"
        "✔ Structured roadmap\n"
        "✔ Placement guidance\n\n"
        "Would you like a free career counselling session?"
    )

    if emotion == "Fear":
        return (
            "It's completely normal to feel uncertain about your future. "
            "Professional courses like ACCA (global), CA (India), or CMA "
            "provide clear career paths and strong job security."
            + base_pitch
        )

    elif emotion == "Sadness":
        return (
            "I understand this phase can feel overwhelming. "
            "The right professional qualification can change your confidence and future."
            + base_pitch
        )

    elif emotion == "Anger":
        return (
            "I’m sorry if your academic journey has been frustrating. "
            "With the right mentorship, courses like ACCA, CA, or CMA become structured and manageable."
            + base_pitch
        )

    elif emotion == "Joy":
        return (
            "That’s great to hear! If you're ambitious, ACCA, CA, or CMA "
            "can help you build a high-paying global career."
            + base_pitch
        )

    else:
        return (
            "Are you currently exploring career options after +2 or graduation? "
            "ACCA, CA, and CMA are highly respected professional finance qualifications."
            + base_pitch
        )

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
    requests.post(url, headers=supabase_headers, json=data)

def fetch_chats():
    url = f"{SUPABASE_URL}/rest/v1/chats?select=*"
    response = requests.get(url, headers=supabase_headers)
    if response.status_code == 200:
        return pd.DataFrame(response.json())
    return pd.DataFrame()

# -----------------------------
# SESSION STATE
# -----------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "lead_name" not in st.session_state:
    st.session_state.lead_name = None

if "lead_phone" not in st.session_state:
    st.session_state.lead_phone = None

if "interested_course" not in st.session_state:
    st.session_state.interested_course = None

# -----------------------------
# CHAT INTERFACE
# -----------------------------
user_input = st.chat_input("Ask me about ACCA, CA, CMA or your career doubts...")

if user_input:

    emotion, confidence = analyze_emotion(user_input)
    bot_reply = generate_response(emotion, user_input)

    st.session_state.chat_history.append(("user", user_input))
    st.session_state.chat_history.append(("assistant", bot_reply))

    insert_chat({
        "user_message": user_input,
        "detected_emotion": emotion,
        "confidence": confidence,
        "bot_response": bot_reply,
        "lead_name": st.session_state.lead_name,
        "lead_phone": st.session_state.lead_phone,
        "interested_course": st.session_state.interested_course
    })

# Display chat
for role, message in st.session_state.chat_history:
    with st.chat_message(role):
        st.write(message)

# -----------------------------
# LEAD CAPTURE SECTION
# -----------------------------
st.markdown("---")
st.subheader("📞 Get Free Counselling")

with st.form("lead_form"):
    name = st.text_input("Your Name")
    phone = st.text_input("Phone Number")
    course = st.selectbox("Interested Course", ["ACCA", "CA", "CMA", "Not Sure"])

    submitted = st.form_submit_button("Request Call Back")

    if submitted:
        st.session_state.lead_name = name
        st.session_state.lead_phone = phone
        st.session_state.interested_course = course

        st.success("Our counsellor will contact you shortly!")

# -----------------------------
# ADMIN SECTION
# -----------------------------
st.markdown("---")
st.subheader("Admin Access")

if "admin" not in st.session_state:
    st.session_state.admin = False

if not st.session_state.admin:
    if st.checkbox("Login as Admin"):
        pin = st.text_input("Enter PIN", type="password")
        if st.button("Login"):
            if pin == "8948":
                st.session_state.admin = True
                st.rerun()
            else:
                st.error("Incorrect PIN")

if st.session_state.admin:
    st.subheader("📊 Leads & Chat Logs")

    df = fetch_chats()
    if not df.empty:
        st.dataframe(df, use_container_width=True)

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        output.seek(0)

        st.download_button(
            "Download Excel",
            output,
            "leads_and_chats.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    if st.button("Logout"):
        st.session_state.admin = False
        st.rerun()
