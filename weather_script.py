import os
import requests
from supabase import create_client

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

# Logging
logging.basicConfig(level=logging.INFO)

def fetch_weather_data(base_url, lat, lon, api_key):
    request_url = f"{base_url}?lat={lat}&lon={lon}&appid={api_key}"
    response = requests.get(request_url)
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Failed to fetch weather data: {response.status_code}")
        return {}

def parse_weather_data(data, lat=40.7128, lon=-74.0060, city='New York'):
    forecast_list = data.get('list', [])
    first_8_filtered = []
    for entry in forecast_list[:8]:
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
            "lat": float(lat),
            "lon": float(lon),
            "city": city
        }
        first_8_filtered.append(filtered_data)
    return first_8_filtered

def insert_into_supabase(supabase_url, supabase_key, table_name, data):
    supabase = create_client(supabase_url, supabase_key)
    try:
        response = supabase.table(table_name).insert(data).execute()
        logging.info(f"Data inserted into Supabase: {response}")
    except Exception as e:
        logging.error(f"Error inserting data into Supabase: {e}")

def format_weather_data_html(data):
    if not data:
        city_name = 'Unknown City'
    else:
        city_name = data[0]['city']
        
    email_content = f"""
    <html>
        <body>
            <h2>24-Hour Weather Forecast for {city_name}</h2>
            <table border="1" cellpadding="5" cellspacing="0">
                <tr>
                    <th>Date & Time</th>
                    <th>Temperature (°F)</th>
                    <th>Feels Like (°F)</th>
                    <th>Humidity (%)</th>
                    <th>Condition</th>
                    <th>Wind Speed (mph)</th>
                    <th>Wind Direction (°)</th>
                    <th>Gusts (mph)</th>
                    <th>Visibility (meters)</th>
                </tr>
    """
    for entry in data:
        email_content += f"""
                <tr>
                    <td>{entry['dt_txt']}</td>
                    <td>{entry['temp_f']}</td>
                    <td>{entry['feels_like_f']}</td>
                    <td>{entry['humidity']}</td>
                    <td>{entry['main']} - {entry['description']}</td>
                    <td>{entry['speed']}</td>
                    <td>{entry['deg']}</td>
                    <td>{entry.get('gust', 'N/A')}</td>
                    <td>{entry.get('visibility', 'N/A')}</td>
                </tr>
        """
    email_content += """
            </table>
        </body>
    </html>
    """
    return email_content

def send_html_email(subject, html_body, from_email, to_emails, email_password):
    msg = MIMEMultipart('alternative')
    msg['From'] = from_email
    msg['To'] = ", ".join(to_emails)
    msg['Subject'] = subject

    part = MIMEText(html_body, 'html', 'utf-8')
    msg.attach(part)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(from_email, email_password)
            server.sendmail(from_email, to_emails, msg.as_string())
        logging.info("HTML email sent to multiple recipients.")
    except Exception as e:
        logging.error(f"Error sending HTML email: {e}")

def determine_severe_weather(forecast_data):
    severe_conditions = []
    for entry in forecast_data:
        weather_main = entry.get('main', '').lower()
        weather_description = entry.get('description', '').lower()
        if 'rain' in weather_main or 'rain' in weather_description:
            severe_conditions.append('RAIN')
        if 'snow' in weather_main or 'snow' in weather_description:
            severe_conditions.append('SNOW')
        if 'ice' in weather_main or 'ice' in weather_description:
            severe_conditions.append('ICE')
        wind_speed = entry.get('speed', 0)
        if wind_speed > 20:
            severe_conditions.append('HIGH WINDS')
        temp_f = entry.get('temp_f', 0)
        if temp_f < 32:
            severe_conditions.append('EXTREMELY COLD')
        if temp_f > 100:
            severe_conditions.append('EXTREMELY HOT')
    severe_conditions = list(set(severe_conditions))
    return severe_conditions

def generate_email_subject(severe_conditions, city):
    if not severe_conditions:
        return f"Your 24-Hour Weather Forecast for {city}"
    condition_messages = {
        'RAIN': "RAIN EXPECTED IN THE NEXT 24 HOURS",
        'SNOW': "SNOW EXPECTED IN THE NEXT 24 HOURS",
        'ICE': "ICE CONDITIONS IN THE NEXT 24 HOURS",
        'HIGH WINDS': "HIGH WINDS EXPECTED IN THE NEXT 24 HOURS",
        'EXTREMELY COLD': "EXTREMELY COLD TEMPERATURES IN THE NEXT 24 HOURS",
        'EXTREMELY HOT': "EXTREMELY HOT TEMPERATURES IN THE NEXT 24 HOURS"
    }
    priority = ['SNOW', 'ICE', 'RAIN', 'EXTREMELY HOT', 'EXTREMELY COLD', 'HIGH WINDS']
    severe_conditions_sorted = sorted(
        severe_conditions,
        key=lambda x: priority.index(x) if x in priority else len(priority)
    )
    alert_messages = [condition_messages[cond] for cond in severe_conditions_sorted]
    subject = "; ".join(alert_messages)
    return subject

def main():
    
    SUPABASE_URL = os.environ["SUPABASE_URL"]
    SUPABASE_KEY = os.environ["SUPABASE_KEY"]
    BASE_URL = os.environ["BASE_URL"]
    API_KEY = os.environ["API_KEY"]
    EMAIL_USER = os.environ["EMAIL_USER"]
    EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
    TO_EMAIL = os.environ["TO_EMAIL"]
    LATITUDE = os.environ["LATITUDE"]
    LONGITUDE = os.environ["LONGITUDE"]
    CITY = os.environ["CITY"]

    # Split the TO_EMAIL string into a list of emails
    to_emails = [email.strip() for email in TO_EMAIL.split(",")]

    # Fetch weather data
    weather_data = fetch_weather_data(BASE_URL, LATITUDE, LONGITUDE, API_KEY)
    forecast = parse_weather_data(weather_data, lat=LATITUDE, lon=LONGITUDE, city=CITY)

    # Insert into Supabase
    if forecast:
        insert_into_supabase(SUPABASE_URL, SUPABASE_KEY, "weather", forecast)
    else:
        logging.warning("No weather data to insert into Supabase.")

    # Email Sending Phase
    if forecast:
        severe_conditions = determine_severe_weather(forecast)
        logging.info(f"Severe conditions found: {severe_conditions}")
        email_subject = generate_email_subject(severe_conditions, CITY)
        email_body = format_weather_data_html(forecast)
        send_html_email(
            subject=email_subject,
            html_body=email_body,
            from_email=EMAIL_USER,
            to_emails=to_emails,
            email_password=EMAIL_PASSWORD
        )
    else:
        logging.warning("No weather data available to send via email.")

if __name__ == "__main__":
    main()
