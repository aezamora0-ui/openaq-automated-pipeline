"""
OpenAQ Data Ingestion Pipeline
------------------------------
Automated ETL script that extracts real-time PM2.5 telemetry from the OpenAQ API,
transforms the payload, and upserts it to a Supabase PostgreSQL database.
"""

import os
import requests
from supabase import create_client, Client

def load_env_file(filename: str = ".env") -> None:
    """Loads environment variables from a local .env file relative to the script directory."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(script_dir, filename)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                os.environ[key] = value

def extract_pm25_telemetry(sensor_id: int, api_key: str) -> list:
    """Extracts raw PM2.5 telemetry data from OpenAQ API v3."""
    url = f"https://api.openaq.org/v3/sensors/{sensor_id}/measurements"
    headers = {"X-API-Key": api_key}
    params = {"limit": 5, "page": 1}
    
    print(f"Initiating data extraction for sensor ID: {sensor_id}...")
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json().get("results", [])
    else:
        print(f"[ERROR] API Request Failed. HTTP Status Code: {response.status_code}")
        response.raise_for_status()

def transform_measurements(raw_results: list, sensor_id: int) -> list:
    """Transforms raw API measurements to match the database schema."""
    records = []
    for result in raw_results:
        # Extract UTC timestamp representing the end of the measurement interval
        utc_time = result.get("period", {}).get("datetimeTo", {}).get("utc")
        record = {
            "sensor_id": sensor_id,
            "reading_time": utc_time,
            "pm25_value": result.get("value")
        }
        records.append(record)
        print(f"Mapped record: {record['reading_time']} | PM2.5: {record['pm25_value']}")
    return records

def load_to_supabase(records: list, supabase_url: str, supabase_key: str) -> None:
    """Upserts transformed records into the database with conflict-resistant unique constraints."""
    if not records:
        print("[WARNING] Extraction complete: No PM2.5 data found in the current time window.")
        return

    supabase: Client = create_client(supabase_url, supabase_key)
    try:
        # Batch upsert targeting the composite unique constraint (sensor_id, reading_time)
        supabase.table("air_quality_readings").upsert(
            records,
            on_conflict="sensor_id,reading_time"
        ).execute()
        print(f"[SUCCESS] Pipeline complete: {len(records)} records successfully upserted.")
    except Exception as e:
        print(f"[ERROR] Database execution error: {e}")
        raise e

def main() -> None:
    load_env_file()
    
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    openaq_key = os.environ.get("OPENAQ_KEY")
    
    if not all([supabase_url, supabase_key, openaq_key]):
        raise ValueError(
            "Missing environment configuration. "
            "Please ensure SUPABASE_URL, SUPABASE_KEY, and OPENAQ_KEY are set."
        )

    # PM2.5 sensor ID for Location 442 (North Phoenix)
    sensor_id = 765
    
    try:
        raw_data = extract_pm25_telemetry(sensor_id, openaq_key)
        transformed_data = transform_measurements(raw_data, sensor_id)
        load_to_supabase(transformed_data, supabase_url, supabase_key)
    except Exception as e:
        print(f"[CRITICAL] ETL Pipeline failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()
