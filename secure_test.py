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
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://cuhsffgclgxixafljvcq.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "your-service-role-key-here") 

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. API Configuration ---
SENSOR_ID = 442
API_ENDPOINT = "https://api.openaq.org/v2/measurements"

# Query parameters configured for descending chronological retrieval
params = {
    "location_id": SENSOR_ID,
    "parameter": "pm25",
    "limit": 5, 
    "page": 1,
    "order_by": "datetime",
    "sort": "desc"
}

# --- 3. Extract Phase ---
print(f"Initiating data extraction for sensor ID: {SENSOR_ID}...")
response = requests.get(API_ENDPOINT, params=params)

if response.status_code == 200:
    data = response.json()
    records_to_insert = []
    
    # --- 4. Transform Phase ---
    # Parse payload and map values to the target database schema
    for result in data.get('results', []):
        record = {
            "sensor_id": SENSOR_ID,
            "reading_time": result['date']['utc'],
            "pm25_value": result['value']
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
            
            print(f"✅ Pipeline complete: {len(records_to_insert)} records successfully upserted.")
        except Exception as e:
            print(f"❌ Database execution error: {e}")
    else:
        print("⚠️ Extraction complete: No PM2.5 data found in the current time window.")

else:
    print(f"❌ API Request Failed. HTTP Status Code: {response.status_code}")
