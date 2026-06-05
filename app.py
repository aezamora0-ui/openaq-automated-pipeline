import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- 1. Connection ---
# Use your PUBLIC anon key here, NOT your secret service role key!
SUPABASE_URL = "https://cuhsffgclgxixafljvcq.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN1aHNmZmdjbGd4aXhhZmxqdmNxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MDQ0MjkwNSwiZXhwIjoyMDk2MDE4OTA1fQ.uKm8GJaEU6vC4yWdYD9ZIDaUxGpW-bDjJiItKyyYzTw"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# --- 2. Build the UI ---
st.title("🌍 New Delhi Air Quality Dashboard")
st.write("Live PM2.5 readings pulled securely from Supabase.")

# --- 3. Fetch the Data ---
# We grab everything and sort it by time so the chart flows left to right
response = supabase.table("air_quality_readings").select("*").order("reading_time", desc=False).execute()

# --- 4. Display the Data ---
if response.data:
    # Convert the raw database JSON into a clean Pandas Spreadsheet (DataFrame)
    df = pd.DataFrame(response.data)
    
    # Create an interactive line chart
    st.subheader("PM2.5 Trend Over Time")
    st.line_chart(df.set_index("reading_time")["pm25_value"])
    
    # Show the raw data table below it
    st.subheader("Raw Database Records")
    st.dataframe(df)
else:
    st.error("No data found in the database!")
