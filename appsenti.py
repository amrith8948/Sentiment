import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import os

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="Malayalam Sentiment Analyzer")
st.title("Malayalam Sentiment Analysis App")
st.write("Analyze reviews and export results to Excel")

# -----------------------------
# HUGGING FACE API
# -----------------------------

API_URL = "https://api-inference.huggingface.co/models/abhinand/malayalam-llama-7b-instruct"

headers = {
    "Authorization": f"Bearer {st.secrets['HF_TOKEN']}"
}

def query(payload):
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.json()

# -----------------------------
# SESSION STATE (STORE DATA)
# -----------------------------
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(
        columns=["Timestamp", "Name", "Review", "Sentiment"]
    )

# -----------------------------
# USER INPUT
# -----------------------------

name = st.text_input("Enter Your Name")
review = st.text_area("Enter Your Review (Malayalam or English)")

if st.button("Analyze Sentiment"):

    if name and review:

        with st.spinner("Analyzing sentiment..."):

            prompt = f"""
Return ONLY one word: Positive, Negative, or Neutral.

Review: {review}

Answer:
"""

            output = query({"inputs": prompt})

            if isinstance(output, list):
                sentiment = output[0]["generated_text"]
            else:
                sentiment = str(output)

        st.success(f"Sentiment: {sentiment}")

        new_row = pd.DataFrame({
            "Timestamp": [datetime.now()],
            "Name": [name],
            "Review": [review],
            "Sentiment": [sentiment]
        })

        st.session_state.data = pd.concat(
            [st.session_state.data, new_row],
            ignore_index=True
        )

    else:
        st.warning("Please enter both Name and Review.")

# -----------------------------
# DISPLAY TABLE
# -----------------------------

if not st.session_state.data.empty:

    st.subheader("Collected Data")
    st.dataframe(st.session_state.data)

    # Convert to Excel
    excel_file = "sentiment_results.xlsx"
    st.session_state.data.to_excel(excel_file, index=False)

    with open(excel_file, "rb") as f:
        st.download_button(
            label="Download Excel File",
            data=f,
            file_name="sentiment_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
