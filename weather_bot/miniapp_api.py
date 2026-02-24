"""
Минимальный API для Mini App: погода по city или lat/lon.
Запуск: gunicorn -w 1 -b 0.0.0.0:5000 miniapp_api:app
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from dotenv import load_dotenv
from flask import Flask, jsonify, request

from weather_app import WeatherClient

load_dotenv()

app = Flask(__name__)

_weather_client: WeatherClient | None = None


@app.errorhandler(500)
@app.errorhandler(Exception)
def handle_error(err):
    """Всегда возвращаем JSON, чтобы приложение не получало HTML."""
    msg = getattr(err, "message", str(err)) if err else "Ошибка сервера"
    return jsonify({"error": msg}), 500 if not hasattr(err, "code") else getattr(err, "code", 500)


def get_weather_client() -> WeatherClient:
    global _weather_client
    if _weather_client is None:
        api_key = os.getenv("OW_API_KEY", "").strip()
        if not api_key:
            raise ValueError("OW_API_KEY не задан")
        _weather_client = WeatherClient(
            api_key=api_key,
            timeout=int(os.getenv("REQUEST_TIMEOUT", "8")),
            cache_ttl_min=int(os.getenv("CACHE_TTL_MIN", "10")),
        )
    return _weather_client


def _weather_code_from_item(item: dict) -> int:
    """Код погоды OpenWeather (для выбора анимации)."""
    w = item.get("weather") or []
    if w and isinstance(w[0], dict):
        return int(w[0].get("id", 800))
    return 800


def _summarize_day(day_items: list[dict]) -> dict[str, Any]:
    if not day_items:
        return {"temp_min": None, "temp_max": None, "description": "", "code": 800}
    temps = []
    codes = []
    descs = []
    for i in day_items:
        m = i.get("main", {})
        t = m.get("temp")
        if t is not None:
            temps.append(float(t))
        w = i.get("weather") or []
        if w and isinstance(w[0], dict):
            codes.append(w[0].get("id", 800))
            descs.append(w[0].get("description", ""))
    return {
        "temp_min": min(temps) if temps else None,
        "temp_max": max(temps) if temps else None,
        "description": descs[0] if descs else "",
        "code": codes[0] if codes else 800,
    }


@app.route("/api/weather", methods=["GET"])
def api_weather():
    city = request.args.get("city", "").strip()
    lat_s = request.args.get("lat", "").strip()
    lon_s = request.args.get("lon", "").strip()

    client = get_weather_client()
    coords = None

    if lat_s and lon_s:
        try:
            coords = (float(lat_s), float(lon_s))
        except ValueError:
            pass
    if not coords and city:
        coords = client.get_coordinates(city, limit=1)
    if not coords:
        return jsonify({"error": "Укажите city или lat и lon"}), 400

    lat, lon = coords
    current = client.get_current_weather(lat, lon)
    if not current:
        return jsonify({"error": client.last_error or "Не удалось получить погоду"}), 502

    forecast_list = client.get_forecast_5d3h(lat, lon)
    city_name = current.get("name", "")

    # Группировка по дням
    by_day: dict[str, list[dict]] = {}
    for item in forecast_list:
        dt_txt = str(item.get("dt_txt", ""))
        day = dt_txt.split(" ")[0] if " " in dt_txt else dt_txt[:10]
        if day:
            by_day.setdefault(day, []).append(item)

    days_sorted = sorted(by_day.keys())
    today = datetime.utcnow().strftime("%Y-%m-%d") if days_sorted else days_sorted[0]
    tomorrow = days_sorted[1] if len(days_sorted) > 1 else None
    next_3_days = days_sorted[1:4]

    current_code = _weather_code_from_item(current)
    current_weather = current.get("weather") or [{}]
    current_desc = current_weather[0].get("description", "") if current_weather else ""

    tomorrow_summary = None
    if tomorrow and tomorrow in by_day:
        tomorrow_summary = _summarize_day(by_day[tomorrow])
        tomorrow_summary["date"] = tomorrow

    forecast_3 = []
    for d in next_3_days:
        if d in by_day:
            s = _summarize_day(by_day[d])
            s["date"] = d
            forecast_3.append(s)

    main = current.get("main", {})
    wind = current.get("wind", {})

    return jsonify({
        "city": city_name,
        "current": {
            "temp": main.get("temp"),
            "feels_like": main.get("feels_like"),
            "humidity": main.get("humidity"),
            "description": current_desc,
            "code": current_code,
            "wind_speed": wind.get("speed"),
        },
        "tomorrow": tomorrow_summary,
        "forecast": forecast_3,
        "weatherCode": current_code,
    })


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})
