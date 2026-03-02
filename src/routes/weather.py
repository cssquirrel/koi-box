"""Weather endpoints: geocoding proxy, location storage, current weather."""

import logging

import requests
from fastapi import APIRouter, Query

from src.database import get_setting, set_setting
from src.models import WeatherLocationRequest

router = APIRouter(tags=["weather"])
logger = logging.getLogger(__name__)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


@router.get("/weather/geocode")
def geocode(q: str = Query(..., min_length=2)):
    """Search for cities via Open-Meteo geocoding API."""
    try:
        resp = requests.get(GEOCODE_URL, params={"name": q, "count": 5}, timeout=5)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning("Geocode request failed: %s", e)
        return {"results": []}

    results = []
    for r in data.get("results", []):
        results.append({
            "name": r.get("name", ""),
            "admin1": r.get("admin1", ""),
            "country_code": r.get("country_code", ""),
            "latitude": r.get("latitude"),
            "longitude": r.get("longitude"),
        })
    return {"results": results}


@router.post("/weather/location")
def save_location(req: WeatherLocationRequest):
    """Save the user's chosen weather location."""
    set_setting("weather_latitude", req.latitude)
    set_setting("weather_longitude", req.longitude)
    set_setting("weather_display_name", req.display_name)
    return {"ok": True}


@router.get("/weather/location")
def get_location():
    """Return the stored weather location."""
    lat = get_setting("weather_latitude")
    lng = get_setting("weather_longitude")
    name = get_setting("weather_display_name", "")
    if lat is None or lng is None:
        return {"configured": False}
    return {
        "configured": True,
        "latitude": lat,
        "longitude": lng,
        "display_name": name,
    }


@router.get("/weather")
def get_weather():
    """Fetch current weather from Open-Meteo for stored location."""
    lat = get_setting("weather_latitude")
    lng = get_setting("weather_longitude")
    if lat is None or lng is None:
        return {"configured": False}

    unit = get_setting("weather_temp_unit", "fahrenheit")

    try:
        resp = requests.get(
            FORECAST_URL,
            params={
                "latitude": lat,
                "longitude": lng,
                "current": "weather_code,temperature_2m",
                "daily": "sunrise,sunset",
                "timezone": "auto",
                "temperature_unit": unit,
            },
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning("Weather fetch failed: %s", e)
        return {"configured": True, "error": "fetch_failed"}

    current = data.get("current", {})
    daily = data.get("daily", {})
    sunrise_list = daily.get("sunrise", [])
    sunset_list = daily.get("sunset", [])
    return {
        "configured": True,
        "weather_code": current.get("weather_code", 0),
        "temperature": current.get("temperature_2m", 0),
        "unit": unit,
        "sunrise": sunrise_list[0] if sunrise_list else None,
        "sunset": sunset_list[0] if sunset_list else None,
    }
