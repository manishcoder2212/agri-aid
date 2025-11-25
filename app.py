# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import requests
import os
from dotenv import load_dotenv

# -----------------------------
# LOAD environment file (weather.env)
# -----------------------------
load_dotenv("weather.env")   # ← important

app = Flask(__name__)
CORS(app)  # allow API calls from browser

# -----------------------------
# DATA MOCKS
# -----------------------------
CROPS = {
    "wheat": {"soil_pref": {"ph_min": 6.0, "ph_max": 7.5}, "rainfall_min": 300, "season": "rabi"},
    "maize": {"soil_pref": {"ph_min": 5.5, "ph_max": 7.0}, "rainfall_min": 500, "season": "kharif"},
    "groundnut": {"soil_pref": {"ph_min": 5.0, "ph_max": 6.5}, "rainfall_min": 400, "season": "kharif"},
    "soybean": {"soil_pref": {"ph_min": 5.5, "ph_max": 7.0}, "rainfall_min": 450, "season": "kharif"},
}

PEST_WARNINGS = [
    {"name": "stem_borer", "crops": ["maize"], "message": "Stem borer alert — apply pheromone traps early."},
    {"name": "aphids", "crops": ["soybean", "groundnut"], "message": "Aphid activity expected, neem spray recommended."}
]

# -----------------------------
# UTILITY FUNCTIONS
# -----------------------------
def recommend_crops(soil_ph, avg_rainfall_mm):
    scores = []
    for crop, info in CROPS.items():
        ph_ok = info["soil_pref"]["ph_min"] <= soil_ph <= info["soil_pref"]["ph_max"]
        rain_ok = avg_rainfall_mm >= info["rainfall_min"]
        score = int(ph_ok) + int(rain_ok)
        scores.append((crop, score, info))
    scores.sort(key=lambda x: x[1], reverse=True)
    return [{"crop": c, "score": s, "reason": f"ph={info['soil_pref']} rainfall(min)={info['rainfall_min']}"} for c, s, info in scores]

def fertilizer_suggestion(crop, nitrogen_ppm, phosphorus_ppm, potassium_ppm):
    suggestions = []
    if nitrogen_ppm < 200: suggestions.append({"nutrient": "N", "suggestion": "Apply Urea 50 kg/ha"})
    if phosphorus_ppm < 15: suggestions.append({"nutrient": "P", "suggestion": "Apply SSP 100 kg/ha"})
    if potassium_ppm < 150: suggestions.append({"nutrient": "K", "suggestion": "Apply MOP 50 kg/ha"})
    if not suggestions:
        suggestions.append({"nutrient": "OK", "suggestion": "Soil nutrients adequate"})
    return suggestions

def pest_risk_for_crop(crop):
    return [p for p in PEST_WARNINGS if crop in p["crops"]]

# -----------------------------
# WEATHER API INTEGRATION
# -----------------------------
OPENWEATHER_KEY = os.getenv("OPENWEATHER_KEY")

def get_weather_from_api(location):
    if not OPENWEATHER_KEY:
        print("\u26a0\ufe0f No API key found in weather.env")
        return None

    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"q": location, "appid": OPENWEATHER_KEY, "units": "metric"}
        r = requests.get(url, params=params, timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("Weather API error:", e)
        return None

# -----------------------------
# API ROUTES
# -----------------------------
@app.route("/api/crop_suggestions", methods=["POST"])
def crop_suggestions():
    data = request.json
    soil_ph = float(data.get("soil_ph", 6.5))
    rain = float(data.get("avg_rainfall_mm", 400))
    return jsonify({
        "ok": True,
        "suggestions": recommend_crops(soil_ph, rain)
    })

@app.route("/api/soil_analysis", methods=["POST"])
def soil_analysis():
    data = request.json
    return jsonify({
        "ok": True,
        "fertilizer_suggestions": fertilizer_suggestion(
            data.get("crop", "maize"),
            float(data.get("nitrogen_ppm", 200)),
            float(data.get("phosphorus_ppm", 20)),
            float(data.get("potassium_ppm", 200))
        )
    })

@app.route("/api/weather_advisory", methods=["POST"])
def weather_advisory():
    data = request.json
    location = data.get("location", "Sangli, India")

    api_data = get_weather_from_api(location)

    if api_data:
        desc = api_data["weather"][0]["description"]
        temp = api_data["main"]["temp"]

        advisory = {
            "short": f"Current weather: {desc}, {temp}°C",
            "detail": "Based on current data, schedule spraying during low wind hours."
        }
    else:
        advisory = {
            "short": "Mock: Light rain expected",
            "detail": "Delay fertilizer application for 48 hours."
        }

    return jsonify({"ok": True, "advisory": advisory})

@app.route("/api/pest_warning", methods=["POST"])
def pest_warning():
    crop = request.json.get("crop", "").lower()
    warnings = pest_risk_for_crop(crop)
    return jsonify({"ok": True, "warnings": warnings})

@app.route("/api/chatbot", methods=["POST"])
def chatbot():
    msg = request.json.get("message", "").lower()
    if "crop" in msg:
        return jsonify({"reply": "Please share soil pH & rainfall for crop suggestion."})
    return jsonify({"reply": "I can assist with weather, soil, crop and pest advisories."})

# -----------------------------
# RUN SERVER
# -----------------------------
if __name__ == "__main__":
    print("Loaded API Key:", OPENWEATHER_KEY)
    app.run(debug=True, port=5000)
