import os
import requests
from supabase import create_client

# Get secrets from repo variables
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
BASE_URL = os.environ["BASE_URL"]
API_KEY = os.environ["API_KEY"]

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

lat = 40.7128  
lon = -74.0060 
city = 'New York'

request_url = f"{BASE_URL}?lat={lat}&lon={lon}&appid={API_KEY}"
print("Request URL:", request_url)

response = requests.get(request_url)
if response.status_code == 200:
    data = response.json()
    forecast_list = data['list'] # Extract the 'list' key
else:
    print("An error occurred.")
    data = {}
    forecast_list = []

# Extract the first 8 entries (data is for 3 hour intervals, so this would give us 24 hours)
first_8_filtered = []
for entry in forecast_list[:8]:
    # Convert temperature from Kelvin to Fahrenheit
    temp_f = (entry["main"]["temp"] - 273.15) * 9 / 5 + 32
    feels_like_f = (entry["main"]["feels_like"] - 273.15) * 9 / 5 + 32

    filtered_data = {
        "temp_f": round(temp_f, 2),
        "feels_like_f": round(feels_like_f, 2),
        "humidity": entry["main"]["humidity"],
        "main": entry["weather"][0]["main"],
        "description": entry["weather"][0]["description"],
        "speed": entry["wind"]["speed"],
        "deg": entry["wind"]["deg"],
        "gust": entry["wind"].get("gust"),
        "visibility": entry.get("visibility"),
        "dt_txt": entry["dt_txt"],
        "lat": lat,
        "lon": lon,
        "city": city
    }
    first_8_filtered.append(filtered_data)

try:
    response = supabase.table("weather").insert(first_8_filtered).execute()
    print("Insert response:", response)
except Exception as e:
    print("Error inserting data:", e)
