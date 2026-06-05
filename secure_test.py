"""
OpenAQ Data Ingestion Pipeline
------------------------------
Automated ETL script that extracts real-time PM2.5 telemetry from the OpenAQ API,
transforms the JSON payload to match the database schema, and loads the data into 
a Supabase PostgreSQL database using conflict-resistant upsert operations.
"""

import os
import requests
from supabase import create_client, Client

# --- 1. Infrastructure & Authentication ---
# Secrets are injected via CI/CD environment variables (e.g., GitHub Actions)
# Utilizing the service_role key to bypass RLS for automated backend ingestion
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. API Configuration ---
# In OpenAQ v3, we query a specific sensor ID instead of a location ID.
# For location 442 (North Phoenix), the sensor ID for PM2.5 is 765.
SENSOR_ID = 765
API_ENDPOINT = f"https://api.openaq.org/v3/sensors/{SENSOR_ID}/measurements"
OPENAQ_KEY = os.environ.get("OPENAQ_KEY", "bb995982779def63e34ed09672a4fcad8da94961f46e47842d1a9d93219b1631")

headers = {
    "X-API-Key": OPENAQ_KEY
}

# Query parameters configured for descending chronological retrieval
params = {
    "limit": 5, 
    "page": 1
}

# --- 3. Extract Phase ---
print(f"Initiating data extraction for sensor ID: {SENSOR_ID}...")
response = requests.get(API_ENDPOINT, headers=headers, params=params)

if response.status_code == 200:
    data = response.json()
    records_to_insert = []
    
    # --- 4. Transform Phase ---
    # Parse payload and map values to the target database schema
    for result in data.get('results', []):
        utc_time = result.get("period", {}).get("datetimeTo", {}).get("utc")
        record = {
            "sensor_id": SENSOR_ID,
            "reading_time": utc_time,
            "pm25_value": result.get("value")
        }
        records_to_insert.append(record)
        print(f"Mapped record: {record['reading_time']} | PM2.5: {record['pm25_value']}")

    # --- 5. Load Phase ---
    if records_to_insert:
        try:
            # Execute batch upsert. 
            # on_conflict targets the composite unique constraint to guarantee idempotency
            db_response = supabase.table("air_quality_readings").upsert(
                records_to_insert, 
                on_conflict="sensor_id,reading_time"
            ).execute()
            
            print(f"[SUCCESS] Pipeline complete: {len(records_to_insert)} records successfully upserted.")
        except Exception as e:
            print(f"[ERROR] Database execution error: {e}")
    else:
        print("[WARNING] Extraction complete: No PM2.5 data found in the current time window.")

else:
    print(f"[ERROR] API Request Failed. HTTP Status Code: {response.status_code}")


