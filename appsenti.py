import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from io import BytesIO

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="Sentiment Analyzer")
st.title("English + Manglish Sentiment Analysis App")

# -----------------------------
# HUGGING FACE ROUTER API
# -----------------------------
API_URL = "https://router.huggingface.co/hf-inference/models/cardiffnlp/twitter-xlm-roberta-base-sentiment"

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
# USER SUBMISSION SECTION
# -----------------------------
st.subheader("Submit Your Review")

name = st.text_input("Enter Your Name", key="name_input")
review = st.text_area("Enter Your Review (English / Manglish)", key="review_input")

if st.button("Submit Review"):

    if name and review:

        with st.spinner("Analyzing sentiment..."):

            output = query({"inputs": review})

        if output is None:
            st.stop()

        try:
            # Model returns list of labels sorted by score
            result = output[0]

            sentiment = result["label"]
            confidence = round(result["score"], 4)

            # Clean label format
            sentiment = sentiment.replace("LABEL_0", "Negative") \
                                 .replace("LABEL_1", "Neutral") \
                                 .replace("LABEL_2", "Positive")

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

            # Auto refresh
            st.rerun()

        except Exception:
            st.error("Unexpected API response format")
            st.write(output)

    else:
        st.warning("Please enter both Name and Review.")

# -----------------------------
# ADMIN LOGIN SECTION
# -----------------------------
st.markdown("---")
st.subheader("Admin Access")

if not st.session_state.admin_authenticated:

    if st.checkbox("Login as Admin"):
        pin = st.text_input("Enter 4-digit PIN", type="password")

        if st.button("Login"):
            if pin == "8948":
                st.session_state.admin_authenticated = True
                st.success("Admin Access Granted")
                st.rerun()
            else:
                st.error("Incorrect PIN")

# -----------------------------
# ADMIN DASHBOARD
# -----------------------------
if st.session_state.admin_authenticated:

    st.markdown("---")
    st.subheader("Admin Dashboard")

    if not st.session_state.data.empty:

        st.dataframe(st.session_state.data)

        # Create Excel file in memory
        output_excel = BytesIO()
        with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
            st.session_state.data.to_excel(
                writer,
                index=False,
                sheet_name="Sentiment Results"
            )

        output_excel.seek(0)

        st.download_button(
            label="Download Excel File",
            data=output_excel,
            file_name="sentiment_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    else:
        st.info("No data available yet.")

    if st.button("Logout Admin"):
        st.session_state.admin_authenticated = False
        st.rerun()
