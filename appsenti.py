import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.title("Malayalam Sentiment Analysis App")

# Hugging Face API
API_URL = "https://api-inference.huggingface.co/models/abhinand/malayalam-llama-7b-instruct"
headers = {"Authorization": f"Bearer {st.secrets['HF_TOKEN']}"}

def query(payload):
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.json()

name = st.text_input("Enter Your Name")
review = st.text_area("Enter Your Review (Malayalam or English)")

if st.button("Analyze Sentiment"):

    if name and review:

        prompt = f"""
        Classify the sentiment of the following review as 
        Positive, Negative, or Neutral.

        Review: {review}

        Sentiment:
        """

        output = query({"inputs": prompt})

        if isinstance(output, list):
            sentiment_result = output[0]["generated_text"]
        else:
            sentiment_result = str(output)

        st.success("Model Response:")
        st.write(sentiment_result)

        # -------- Google Sheets Saving --------

        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]

        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            st.secrets["gcp_service_account"], scope
        )

        client = gspread.authorize(credentials)
        sheet = client.open("Sentiment_Data").sheet1

        sheet.append_row([
            str(datetime.now()),
            name,
            review,
            sentiment_result
        ])

        st.success("Data Saved to Google Sheets!")

    else:
        st.warning("Please enter both name and review.")
