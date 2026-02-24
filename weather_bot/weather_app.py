from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()


class OpenWeatherCache:
    """Simple file cache for OpenWeather responses."""

    def __init__(self, cache_dir: str | Path = ".cache", ttl_seconds: int = 600) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds

    def _cache_file(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def get(self, key: str) -> Any | None:
        file_path = self._cache_file(key)
        if not file_path.exists():
            return None
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            created_at = float(payload.get("created_at", 0))
            if time.time() - created_at > self.ttl_seconds:
                return None
            return payload.get("data")
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            return None

    def set(self, key: str, data: Any) -> None:
        file_path = self._cache_file(key)
        payload = {"created_at": time.time(), "data": data}
        try:
            file_path.write_text(
                json.dumps(payload, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            # Cache must never block weather retrieval.
            return


class WeatherClient:
    BASE = "https://api.openweathermap.org"

    def __init__(self, api_key: str, timeout: int = 8, cache_ttl_min: int = 10) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self.last_error: str | None = None
        self.cache = OpenWeatherCache(ttl_seconds=max(cache_ttl_min, 1) * 60)

    def _cache_key(self, endpoint: str, params: dict[str, Any]) -> str:
        normalized = "&".join(f"{k}={params[k]}" for k in sorted(params))
        return f"{endpoint}?{normalized}"

    def _request_json(
        self,
        endpoint: str,
        params: dict[str, Any],
        use_cache: bool = True,
    ) -> Any | None:
        self.last_error = None
        merged = {"appid": self.api_key, **params}
        cache_key = self._cache_key(endpoint, merged)
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        url = f"{self.BASE}{endpoint}"
        delays = [1, 2, 4]
        attempts = len(delays) + 1

        for attempt in range(attempts):
            try:
                response = requests.get(url, params=merged, timeout=self.timeout)
            except requests.RequestException:
                self.last_error = "Сетевая ошибка. Проверьте подключение и повторите позже."
                return None

            if response.status_code == 429:
                if attempt < len(delays):
                    time.sleep(delays[attempt])
                    continue
                self.last_error = "Слишком много запросов к погодному API. Повторите позже."
                return None

            if 400 <= response.status_code < 600:
                self.last_error = f"Ошибка сервиса погоды ({response.status_code})."
                return None

            try:
                data = response.json()
            except ValueError:
                self.last_error = "Некорректный ответ от сервиса погоды."
                return None

            if use_cache:
                self.cache.set(cache_key, data)
            return data

        self.last_error = "Не удалось получить данные о погоде."
        return None

    def get_coordinates(self, city: str, limit: int = 1) -> tuple[float, float] | None:
        params = {"q": city, "limit": limit, "lang": "ru"}
        data = self._request_json("/geo/1.0/direct", params, use_cache=True)
        if not data or not isinstance(data, list):
            if self.last_error is None:
                self.last_error = "Город не найден."
            return None
        first = data[0] if data else None
        if not isinstance(first, dict):
            self.last_error = "Город не найден."
            return None
        lat = first.get("lat")
        lon = first.get("lon")
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            return float(lat), float(lon)
        self.last_error = "Город не найден."
        return None

    def get_current_weather(self, lat: float, lon: float) -> dict[str, Any]:
        params = {"lat": lat, "lon": lon, "units": "metric", "lang": "ru"}
        data = self._request_json("/data/2.5/weather", params, use_cache=True)
        if isinstance(data, dict):
            return data
        return {}

    def get_forecast_5d3h(self, lat: float, lon: float) -> list[dict[str, Any]]:
        params = {"lat": lat, "lon": lon, "units": "metric", "lang": "ru"}
        data = self._request_json("/data/2.5/forecast", params, use_cache=True)
        if not isinstance(data, dict):
            return []
        items = data.get("list")
        if isinstance(items, list):
            return [i for i in items if isinstance(i, dict)]
        return []

    def get_air_pollution(self, lat: float, lon: float) -> dict[str, Any]:
        params = {"lat": lat, "lon": lon}
        data = self._request_json("/data/2.5/air_pollution", params, use_cache=True)
        if not isinstance(data, dict):
            return {}
        lst = data.get("list")
        if isinstance(lst, list) and lst and isinstance(lst[0], dict):
            components = lst[0].get("components")
            if isinstance(components, dict):
                return components
        return {}


class AirQualityAnalyzer:
    def analyze_air_pollution(
        self,
        components: dict[str, Any],
        extended: bool = False,
    ) -> dict[str, Any]:
        if not components:
            return {
                "status": "Нет данных",
                "summary": "Не удалось получить компоненты качества воздуха.",
                "details": {},
            }

        pm25 = float(components.get("pm2_5", 0))
        pm10 = float(components.get("pm10", 0))
        no2 = float(components.get("no2", 0))
        o3 = float(components.get("o3", 0))

        score = 0
        score += 3 if pm25 > 35 else 2 if pm25 > 15 else 1 if pm25 > 5 else 0
        score += 3 if pm10 > 50 else 2 if pm10 > 25 else 1 if pm10 > 10 else 0
        score += 2 if no2 > 100 else 1 if no2 > 40 else 0
        score += 2 if o3 > 120 else 1 if o3 > 60 else 0

        if score <= 2:
            status = "Хорошее"
            summary = "Качество воздуха в норме."
        elif score <= 5:
            status = "Умеренное"
            summary = "Допустимо для большинства людей."
        elif score <= 8:
            status = "Повышенное загрязнение"
            summary = "Чувствительным группам стоит сократить время на улице."
        else:
            status = "Высокое загрязнение"
            summary = "Рекомендуется ограничить активность на открытом воздухе."

        result = {
            "status": status,
            "summary": summary,
            "details": {},
        }
        if extended:
            result["details"] = {
                "co": components.get("co", 0),
                "no": components.get("no", 0),
                "no2": components.get("no2", 0),
                "o3": components.get("o3", 0),
                "so2": components.get("so2", 0),
                "pm2_5": components.get("pm2_5", 0),
                "pm10": components.get("pm10", 0),
                "nh3": components.get("nh3", 0),
            }
        return result


def _build_default_client() -> WeatherClient:
    api_key = os.getenv("OW_API_KEY", "")
    timeout = int(os.getenv("REQUEST_TIMEOUT", "8"))
    cache_ttl = int(os.getenv("CACHE_TTL_MIN", "10"))
    return WeatherClient(api_key=api_key, timeout=timeout, cache_ttl_min=cache_ttl)


_default_client = _build_default_client()
_analyzer = AirQualityAnalyzer()


def get_coordinates(city: str, limit: int = 1) -> tuple[float, float] | None:
    return _default_client.get_coordinates(city=city, limit=limit)


def get_current_weather(lat: float, lon: float) -> dict[str, Any]:
    return _default_client.get_current_weather(lat=lat, lon=lon)


def get_forecast_5d3h(lat: float, lon: float) -> list[dict[str, Any]]:
    return _default_client.get_forecast_5d3h(lat=lat, lon=lon)


def get_air_pollution(lat: float, lon: float) -> dict[str, Any]:
    return _default_client.get_air_pollution(lat=lat, lon=lon)


def analyze_air_pollution(components: dict[str, Any], extended: bool = False) -> dict[str, Any]:
    return _analyzer.analyze_air_pollution(components=components, extended=extended)


def get_last_error() -> str | None:
    return _default_client.last_error
