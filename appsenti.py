import streamlit as st
import requests
import pandas as pd
from io import BytesIO

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="Emotion Analyzer", layout="centered")
st.title("Emotion Analysis App (English + Manglish)")

# -----------------------------
# LOAD SECRETS
# -----------------------------
HF_TOKEN = st.secrets["HF_TOKEN"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# -----------------------------
# HUGGING FACE EMOTION MODEL
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
        st.write(response.text)
        return None, None

    try:
        output = response.json()[0]
        best = sorted(output, key=lambda x: x["score"], reverse=True)[0]

        emotion = best["label"].capitalize()
        confidence = round(best["score"], 4)

        return emotion, confidence

    except Exception:
        st.error("Unexpected model response format.")
        st.write(response.text)
        return None, None

# -----------------------------
# SUPABASE CONFIG
# -----------------------------
supabase_headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

def insert_review(data):
    url = f"{SUPABASE_URL}/rest/v1/reviews"

    response = requests.post(
        url,
        headers=supabase_headers,
        json=data
    )

    if response.status_code not in [200, 201]:
        st.error(f"Supabase Insert Error: {response.status_code}")
        st.write(response.text)
        return False
    return True


def fetch_reviews():
    url = f"{SUPABASE_URL}/rest/v1/reviews?select=*"

    response = requests.get(
        url,
        headers=supabase_headers
    )

    if response.status_code != 200:
        st.error(f"Supabase Fetch Error: {response.status_code}")
        st.write(response.text)
        return pd.DataFrame()

    return pd.DataFrame(response.json())

# -----------------------------
# USER INPUT SECTION
# -----------------------------
st.subheader("Submit Your Review")

name = st.text_input("Enter Your Name")
review = st.text_area("Enter Your Review (English / Manglish)")

if st.button("Submit Review"):

    if name and review:

        with st.spinner("Analyzing emotion..."):
            emotion, confidence = analyze_emotion(review)

        if emotion:

            data = {
                "name": name,
                "review": review,
                "sentiment": emotion,   # Column name remains same in DB
                "confidence": confidence
            }

            success = insert_review(data)

            if success:
                st.success(f"Detected Emotion: {emotion}")
                st.info(f"Confidence: {confidence}")
                st.rerun()

    else:
        st.warning("Please enter both Name and Review.")

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
                st.success("Admin access granted")
                st.rerun()
            else:
                st.error("Incorrect PIN")

# -----------------------------
# ADMIN DASHBOARD
# -----------------------------
if st.session_state.admin_logged_in:

    st.markdown("---")
    st.subheader("Admin Dashboard")

    df = fetch_reviews()

    if not df.empty:

        st.dataframe(df, use_container_width=True)

        # Excel export
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)

        output.seek(0)

        st.download_button(
            label="Download Excel File",
            data=output,
            file_name="emotion_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    else:
        st.info("No data available yet.")

    if st.button("Logout Admin"):
        st.session_state.admin_logged_in = False
        st.rerun()
