import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from io import BytesIO

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="Malayalam Sentiment Analyzer")
st.title("Malayalam Sentiment Analysis App")

# -----------------------------
# HUGGING FACE API
# -----------------------------
API_URL = "https://router.huggingface.co/hf-inference/models/l3cube-pune/malayalam-sentiment-analysis"

headers = {
    "Authorization": f"Bearer {st.secrets['HF_TOKEN']}",
    "Content-Type": "application/json"
}

def query(payload):
    response = requests.post(API_URL, headers=headers, json=payload)

    if response.status_code != 200:
        st.error(f"API Error: {response.status_code}")
        st.write(response.text)
        return None

    return response.json()

# -----------------------------
# SESSION STATE INITIALIZATION
# -----------------------------
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(
        columns=["Timestamp", "Name", "Review", "Sentiment", "Confidence"]
    )

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

# -----------------------------
# USER INPUT SECTION
# -----------------------------
st.subheader("Submit Your Review")

name = st.text_input("Enter Your Name")
review = st.text_area("Enter Your Review (Malayalam or English)")

if st.button("Submit Review"):

    if name and review:

        with st.spinner("Analyzing sentiment..."):
            output = query({"inputs": review})

        if output is None:
            st.stop()

        try:
            sentiment = output[0][0]["label"]
            confidence = round(output[0][0]["score"], 4)

            new_row = pd.DataFrame({
                "Timestamp": [datetime.now()],
                "Name": [name],
                "Review": [review],
                "Sentiment": [sentiment],
                "Confidence": [confidence]
            })

            st.session_state.data = pd.concat(
                [st.session_state.data, new_row],
                ignore_index=True
            )

            st.success("Review submitted successfully!")

            # Clear inputs and refresh page
            st.session_state["name"] = ""
            st.session_state["review"] = ""
            st.rerun()

        except Exception:
            st.error("Unexpected API response format")
            st.write(output)

    else:
        st.warning("Please enter both Name and Review.")

# -----------------------------
# ADMIN SECTION
# -----------------------------
st.markdown("---")
st.subheader("Admin Access")

admin_option = st.checkbox("Login as Admin")

if admin_option and not st.session_state.admin_authenticated:

    pin = st.text_input("Enter 4-digit PIN", type="password")

    if st.button("Login"):

        if pin == "8948":
            st.session_state.admin_authenticated = True
            st.success("Admin Access Granted")
            st.rerun()
        else:
            st.error("Incorrect PIN")

# -----------------------------
# SHOW DATA ONLY IF ADMIN
# -----------------------------
if st.session_state.admin_authenticated:

    st.markdown("---")
    st.subheader("Admin Dashboard")

    if not st.session_state.data.empty:

        st.dataframe(st.session_state.data)

        # Excel export
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            st.session_state.data.to_excel(
                writer,
                index=False,
                sheet_name="Sentiment Results"
            )

        output.seek(0)

        st.download_button(
            label="Download Excel File",
            data=output,
            file_name="sentiment_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    else:
        st.info("No data available yet.")

    if st.button("Logout Admin"):
        st.session_state.admin_authenticated = False
        st.rerun()
