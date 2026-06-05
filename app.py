"""
OpenAQ AI Dashboard
-------------------
Streamlit front-end for air quality ETL pipeline. 
Connects to Supabase (read-only via RLS) and uses Gemini API for real-time analysis.
"""

import streamlit as st
from supabase import create_client, Client
import pandas as pd
import google.generativeai as genai

# --- 1. Infrastructure & Security ---
# Public endpoints protected by database RLS (Row Level Security)
SUPABASE_URL = "https://cuhsffgclgxixafljvcq.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN1aHNmZmdjbGd4aXhhZmxqdmNxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA0NDI5MDUsImV4cCI6MjA5NjAxODkwNX0.4vI-GE64yKmasfi3tIjNXD9iAuF3DUiD4H8p6eSB2dE"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Fetch LLM API key securely from Streamlit Secrets vault
gemini_key = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=gemini_key)

# --- 2. UI Initialization ---
st.title("🌍 New Delhi Air Quality Dashboard")
st.write("Live PM2.5 data pipeline with real-time AI Executive Briefings.")

# --- 3. Data Ingestion ---
# Fetch chronological time-series data
response = supabase.table("air_quality_readings").select("*").order("reading_time", desc=False).execute()

if response.data:
    df = pd.DataFrame(response.data)
    
    # Render Visualization
    st.subheader("📈 PM2.5 Trend Over Time")
    st.line_chart(df.set_index("reading_time")["pm25_value"])
    
    # --- 4. LLM Integration Layer ---
    st.markdown("---")
    st.subheader("🤖 AI Executive Action Briefing")
    
   with st.spinner("Running API Diagnostic..."):
        try:
            # Test authentication and list permitted models
            allowed_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            st.success("API Key successfully authenticated!")
            st.write("Your key has access to these models:", allowed_models)
        except Exception as e:
            st.error(f"Authentication Failed. Error details: {e}")
        
        # Execute inference via Gemini 1.5 Flash
        model = genai.GenerativeModel("gemini-pro")
        ai_response = model.generate_content(prompt)
        
        # Render output
        st.write(ai_response.text)
        
    st.markdown("---")
    st.subheader("📊 Raw Database Records")
    st.dataframe(df)
else:
    st.error("Data ingestion failed or database is currently empty.")
