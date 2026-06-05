import os
import requests
from supabase import create_client, Client

# --- 1. Credentials ---
OPENAQ_KEY = os.getenv("OPENAQ_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# Initialize the Supabase connection
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# --- 2. Extract: Pull from OpenAQ ---
print("Fetching latest data from OpenAQ...")
sensor_id = 442
url = f"https://api.openaq.org/v3/sensors/{sensor_id}/measurements"
headers = {"X-API-Key": OPENAQ_KEY}

# Fetch data dynamically for the last 24 hours
datetime_from = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
params = {
    "limit": 5,
    "page": 1,
    "datetime_from": datetime_from
}

response = requests.get(url, headers=headers, params=params)
data = response.json()

# --- 3. Transform & Load ---
if "results" in data and len(data["results"]) > 0:
    records_to_insert = []
    
    for reading in data["results"]:
        value = reading.get("value")
        utc_time = reading.get("period", {}).get("datetimeTo", {}).get("utc") 
        
        # Map fields to match database schema
        record = {
            "sensor_id": sensor_id,
            "reading_time": utc_time,
            "pm25_value": value
        }
        records_to_insert.append(record)
        print(f"Mapped record: {record['reading_time']} | PM2.5: {record['pm25_value']}")
        
    print(f"Preparing to load {len(records_to_insert)} records to the cloud...")
    
    # Insert records into Supabase
    db_response = supabase.table("air_quality_readings").upsert(records_to_insert, on_conflict="sensor_id,reading_time").execute()
    print("[SUCCESS] Data has been written to Supabase.")
else:
    print("[WARNING] No recent data retrieved from OpenAQ.")
