import streamlit as st
import requests
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --------------------------------
# PAGE CONFIG
# --------------------------------
st.set_page_config(page_title="Malayalam Sentiment Analyzer")
st.title("Malayalam Sentiment Analysis App")

# --------------------------------
# HUGGING FACE SETUP
# --------------------------------
API_URL = "https://api-inference.huggingface.co/models/abhinand/malayalam-llama-7b-instruct"

headers = {
    "Authorization": f"Bearer {st.secrets['HF_TOKEN']}"
}

def query(payload):
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.json()

# --------------------------------
# GOOGLE SHEETS SETUP
# --------------------------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

credentials = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp_service_account"], scope
)

client = gspread.authorize(credentials)

# YOUR SHEET ID
SHEET_ID = "1u4cJVVTp3oPTPKoZo4eomnt2jcZfmLia88xYRvK-okw"

sheet = client.open_by_key(SHEET_ID).sheet1

# --------------------------------
# USER INPUT
# --------------------------------
name = st.text_input("Enter Your Name")
review = st.text_area("Enter Your Review (Malayalam or English)")

if st.button("Analyze Sentiment"):

    if name and review:

        with st.spinner("Analyzing..."):

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

        # Append row to Google Sheet
        sheet.append_row([
            str(datetime.now()),
            name,
            review,
            sentiment
        ])

        st.success("Saved to Google Sheet Successfully!")

    else:
        st.warning("Please enter both Name and Review.")
