from __future__ import annotations

import os
import time
from collections import defaultdict
from datetime import datetime
from typing import Any

import telebot
from dotenv import load_dotenv
from telebot import types

from storage import UserStorage
from weather_app import AirQualityAnalyzer, WeatherClient

load_dotenv()


class TelegramWeatherBot:
    def __init__(self) -> None:
        self.bot_token = os.getenv("BOT_TOKEN", "").strip()
        self.ow_api_key = os.getenv("OW_API_KEY", "").strip()
        self.default_interval_h = int(os.getenv("DEFAULT_NOTIFICATIONS_INTERVAL_H", "2"))
        self.request_timeout = int(os.getenv("REQUEST_TIMEOUT", "8"))
        self.cache_ttl_min = int(os.getenv("CACHE_TTL_MIN", "10"))

        if not self.bot_token:
            raise ValueError("BOT_TOKEN не найден. Добавьте токен в .env")
        if not self.ow_api_key:
            raise ValueError("OW_API_KEY не найден. Добавьте ключ OpenWeather в .env")

        self.bot = telebot.TeleBot(self.bot_token, parse_mode="HTML")
        self.storage = UserStorage("User_Data.json")
        self.weather = WeatherClient(
            api_key=self.ow_api_key,
            timeout=self.request_timeout,
            cache_ttl_min=self.cache_ttl_min,
        )
        self.air_analyzer = AirQualityAnalyzer()

        self.user_states: dict[int, dict[str, Any]] = defaultdict(dict)
        self.forecast_cache: dict[int, dict[str, list[dict[str, Any]]]] = {}

        # Словарь переводов описаний погоды (fallback если API вернет EN)
        self.weather_translations = {
            "clear sky": "ясно",
            "few clouds": "небольшая облачность",
            "scattered clouds": "переменная облачность",
            "broken clouds": "облачно",
            "overcast clouds": "пасмурно",
            "light rain": "небольшой дождь",
            "moderate rain": "умеренный дождь",
            "heavy rain": "сильный дождь",
            "light snow": "небольшой снег",
            "moderate snow": "умеренный снег",
            "heavy snow": "сильный снег",
            "mist": "туман",
            "fog": "туман",
            "haze": "дымка",
            "dust": "пыль",
            "sand": "песок",
            "thunderstorm": "гроза",
            "drizzle": "морось",
        }

        self._register_handlers()

    def run(self) -> None:
        self.bot.infinity_polling(skip_pending=True)

    def _register_handlers(self) -> None:
        @self.bot.message_handler(commands=["start"])
        def start(message: types.Message) -> None:
            self._check_notifications(message.from_user.id, message.chat.id)
            self._send_main_menu(
                chat_id=message.chat.id,
                text=(
                    "Привет! Я погодный бот.\n"
                    "Выберите действие в меню ниже."
                ),
            )

        @self.bot.message_handler(content_types=["location"])
        def handle_location(message: types.Message) -> None:
            self._check_notifications(message.from_user.id, message.chat.id)
            self._handle_location_message(message)

        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_callback(call: types.CallbackQuery) -> None:
            if call.message and call.from_user:
                self._check_notifications(call.from_user.id, call.message.chat.id)
            self._handle_callback(call)

        @self.bot.message_handler(content_types=["text"])
        def handle_text(message: types.Message) -> None:
            self._check_notifications(message.from_user.id, message.chat.id)
            self._handle_text_message(message)

        @self.bot.inline_handler(lambda query: True)
        def handle_inline(query: types.InlineQuery) -> None:
            self._handle_inline_query(query)

    def _main_menu_markup(self) -> types.ReplyKeyboardMarkup:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        buttons = [
            types.KeyboardButton("Текущая погода"),
            types.KeyboardButton("Прогноз на 5 дней"),
            types.KeyboardButton("Моя геолокация", request_location=True),
            types.KeyboardButton("Сравнить города"),
            types.KeyboardButton("Расширенные данные"),
            types.KeyboardButton("Уведомления"),
        ]
        markup.add(*buttons)
        return markup

    def _send_main_menu(self, chat_id: int, text: str) -> None:
        self.bot.send_message(chat_id, text, reply_markup=self._main_menu_markup())

    def _handle_text_message(self, message: types.Message) -> None:
        user_id = message.from_user.id
        text = (message.text or "").strip()

        if text == "Текущая погода":
            self.user_states[user_id] = {"action": "current_weather"}
            self.bot.send_message(
                message.chat.id,
                "Введите город (например, Москва) или отправьте геолокацию кнопкой «Моя геолокация».",
            )
            return

        if text == "Прогноз на 5 дней":
            self.user_states[user_id] = {"action": "forecast"}
            self.bot.send_message(
                message.chat.id,
                "Введите город для прогноза или отправьте геолокацию.",
            )
            return

        if text == "Сравнить города":
            self.user_states[user_id] = {"action": "compare_city_1"}
            self.bot.send_message(message.chat.id, "Введите первый город:")
            return

        if text == "Расширенные данные":
            self.user_states[user_id] = {"action": "extended_data"}
            self.bot.send_message(
                message.chat.id,
                "Введите город для расширенного анализа (погода + качество воздуха) или отправьте геолокацию.",
            )
            return

        if text == "Уведомления":
            self._show_notifications_menu(message.chat.id, user_id)
            return

        if text == "Моя геолокация":
            self.bot.send_message(
                message.chat.id,
                "Нажмите кнопку «Моя геолокация» (с иконкой скрепки/локации) и отправьте location.",
            )
            return

        state = self.user_states.get(user_id, {})
        action = state.get("action")

        if action == "current_weather":
            self._handle_current_weather_by_city(message, text)
            return

        if action == "forecast":
            self._handle_forecast_by_city(message, text)
            return

        if action == "extended_data":
            self._handle_extended_by_city(message, text)
            return

        if action == "compare_city_1":
            self.user_states[user_id] = {"action": "compare_city_2", "city_1": text}
            self.bot.send_message(message.chat.id, "Введите второй город:")
            return

        if action == "compare_city_2":
            city_1 = state.get("city_1", "")
            self._handle_compare_cities(message.chat.id, city_1, text)
            self.user_states[user_id] = {}
            return

        self._send_main_menu(
            message.chat.id,
            "Не понял команду. Выберите действие из меню.",
        )

    def _handle_location_message(self, message: types.Message) -> None:
        user_id = message.from_user.id
        location = message.location
        if not location:
            self.bot.send_message(message.chat.id, "Пустая геолокация. Пожалуйста, отправьте location.")
            return

        lat = float(location.latitude)
        lon = float(location.longitude)
        user_data = self.storage.load_user(user_id)
        user_data["lat"] = lat
        user_data["lon"] = lon
        user_data.setdefault("notifications", {"enabled": False, "interval_h": self.default_interval_h})
        self.storage.save_user(user_id, user_data)

        state = self.user_states.get(user_id, {})
        action = state.get("action")

        if action == "current_weather":
            self._send_current_weather(message.chat.id, lat, lon)
            self.user_states[user_id] = {}
            return

        if action == "forecast":
            self._send_forecast_menu(message.chat.id, user_id, lat, lon)
            self.user_states[user_id] = {}
            return

        if action == "extended_data":
            self._send_extended_data(message.chat.id, lat, lon)
            self.user_states[user_id] = {}
            return

        self.bot.send_message(message.chat.id, "Геолокация сохранена.")

    def _handle_current_weather_by_city(self, message: types.Message, city: str) -> None:
        self.bot.send_chat_action(message.chat.id, "typing")
        coords = self.weather.get_coordinates(city)
        if not coords:
            self.bot.send_message(message.chat.id, "Город не найден.")
            return

        lat, lon = coords
        user_data = self.storage.load_user(message.from_user.id)
        user_data["city"] = city
        user_data["lat"] = lat
        user_data["lon"] = lon
        user_data.setdefault("notifications", {"enabled": False, "interval_h": self.default_interval_h})
        self.storage.save_user(message.from_user.id, user_data)

        self._send_current_weather(message.chat.id, lat, lon, city=city)
        self.user_states[message.from_user.id] = {}

    def _send_current_weather(self, chat_id: int, lat: float, lon: float, city: str | None = None) -> None:
        self.bot.send_chat_action(chat_id, "typing")
        weather = self.weather.get_current_weather(lat, lon)
        if not weather:
            self.bot.send_message(chat_id, self.weather.last_error or "Не удалось получить погоду.")
            return

        city_name = city or weather.get("name", "Неизвестный город")
        main = weather.get("main", {})
        wind = weather.get("wind", {})
        weather_meta = weather.get("weather", [{}])
        raw_description = weather_meta[0].get("description") or "нет описания"
        description = self._translate_weather_description(raw_description).capitalize()

        msg = (
            f"<b>Текущая погода: {city_name}</b>\n"
            f"🌡 Температура: {main.get('temp', '—')}°C\n"
            f"🤗 Ощущается как: {main.get('feels_like', '—')}°C\n"
            f"💧 Влажность: {main.get('humidity', '—')}%\n"
            f"🌬 Ветер: {wind.get('speed', '—')} м/с\n"
            f"☁️ Состояние: {description}"
        )
        self.bot.send_message(chat_id, msg)

    def _handle_forecast_by_city(self, message: types.Message, city: str) -> None:
        self.bot.send_chat_action(message.chat.id, "typing")
        coords = self.weather.get_coordinates(city)
        if not coords:
            self.bot.send_message(message.chat.id, "Город не найден.")
            return

        lat, lon = coords
        user_data = self.storage.load_user(message.from_user.id)
        user_data["city"] = city
        user_data["lat"] = lat
        user_data["lon"] = lon
        user_data.setdefault("notifications", {"enabled": False, "interval_h": self.default_interval_h})
        self.storage.save_user(message.from_user.id, user_data)

        self._send_forecast_menu(message.chat.id, message.from_user.id, lat, lon, city=city)
        self.user_states[message.from_user.id] = {}

    def _send_forecast_menu(
        self,
        chat_id: int,
        user_id: int,
        lat: float,
        lon: float,
        city: str | None = None,
    ) -> None:
        self.bot.send_chat_action(chat_id, "typing")
        forecast_list = self.weather.get_forecast_5d3h(lat, lon)
        if not forecast_list:
            self.bot.send_message(chat_id, self.weather.last_error or "Не удалось получить прогноз.")
            return

        grouped: dict[str, list[dict[str, Any]]] = {}
        for item in forecast_list:
            dt_txt = str(item.get("dt_txt", ""))
            day = dt_txt.split(" ")[0] if " " in dt_txt else dt_txt[:10]
            if day:
                grouped.setdefault(day, []).append(item)

        if not grouped:
            self.bot.send_message(chat_id, "Нет данных прогноза.")
            return

        self.forecast_cache[user_id] = grouped
        
        # Формируем общий прогноз на 5 дней с эмодзи
        title_city = city or "выбранной точки"
        forecast_lines = [f"<b>Прогноз на 5 дней: {title_city}</b>\n"]
        
        for day in sorted(grouped.keys())[:5]:  # Берем первые 5 дней
            day_items = grouped[day]
            summary = self._get_daily_summary(day_items)
            day_label = self._format_day_label(day)
            
            forecast_lines.append(
                f"{summary['emoji']} <b>{day_label}</b>\n"
                f"   {summary['min_temp']}° / {summary['max_temp']}°C - {summary['description']}\n"
            )
        
        forecast_text = "".join(forecast_lines)
        forecast_text += "\nВыберите день для детального прогноза:"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for day in sorted(grouped.keys())[:5]:
            label = self._format_day_label(day)
            markup.add(types.InlineKeyboardButton(label, callback_data=f"forecast_day|{day}"))
        markup.add(types.InlineKeyboardButton("Назад", callback_data="forecast_back"))

        self.bot.send_message(chat_id, forecast_text, reply_markup=markup)

    def _format_day_label(self, day: str) -> str:
        try:
            parsed = datetime.strptime(day, "%Y-%m-%d")
            return parsed.strftime("%d.%m.%Y")
        except ValueError:
            return day

    def _translate_weather_description(self, description: str) -> str:
        """Переводит описание погоды с английского на русский, если нужно."""
        desc_lower = description.lower().strip()
        # Если уже на русском (содержит кириллицу), возвращаем как есть
        if any("\u0400" <= char <= "\u04FF" for char in description):
            return description
        
        # Ищем перевод
        for en, ru in self.weather_translations.items():
            if en in desc_lower:
                return ru
        
        # Если не нашли точный перевод, возвращаем оригинал
        return description

    def _get_weather_emoji(self, weather_code: int) -> str:
        """Возвращает эмодзи для кода погоды OpenWeather."""
        # Основные группы кодов погоды OpenWeather
        if weather_code == 800:  # Clear sky
            return "☀️"
        elif weather_code == 801:  # Few clouds
            return "🌤️"
        elif weather_code == 802:  # Scattered clouds
            return "⛅"
        elif weather_code == 803 or weather_code == 804:  # Broken/Overcast clouds
            return "☁️"
        elif weather_code >= 200 and weather_code < 300:  # Thunderstorm
            return "⛈️"
        elif weather_code >= 300 and weather_code < 400:  # Drizzle
            return "🌦️"
        elif weather_code >= 500 and weather_code < 600:  # Rain
            return "🌧️"
        elif weather_code >= 600 and weather_code < 700:  # Snow
            return "❄️"
        elif weather_code >= 700 and weather_code < 800:  # Atmosphere (mist, fog, etc.)
            return "🌫️"
        else:
            return "🌡️"

    def _get_daily_summary(self, day_items: list[dict[str, Any]]) -> dict[str, Any]:
        """Получает сводку по дню: мин/макс температура, основное состояние погоды."""
        if not day_items:
            return {"min_temp": "—", "max_temp": "—", "emoji": "🌡️", "description": "нет данных"}
        
        temps = []
        weather_codes = []
        descriptions = []
        
        for item in day_items:
            main = item.get("main", {})
            temp = main.get("temp")
            if isinstance(temp, (int, float)):
                temps.append(float(temp))
            
            weather_list = item.get("weather", [])
            if weather_list and isinstance(weather_list[0], dict):
                code = weather_list[0].get("id")
                desc = weather_list[0].get("description", "")
                if code:
                    weather_codes.append(code)
                if desc:
                    descriptions.append(desc)
        
        min_temp = min(temps) if temps else "—"
        max_temp = max(temps) if temps else "—"
        
        # Берем наиболее частый код погоды или первый
        main_code = weather_codes[0] if weather_codes else 800
        emoji = self._get_weather_emoji(main_code)
        
        # Берем первое описание и переводим если нужно
        raw_desc = descriptions[0] if descriptions else "нет данных"
        description = self._translate_weather_description(raw_desc).capitalize()
        
        return {
            "min_temp": f"{min_temp:.1f}" if isinstance(min_temp, float) else min_temp,
            "max_temp": f"{max_temp:.1f}" if isinstance(max_temp, float) else max_temp,
            "emoji": emoji,
            "description": description,
        }

    def _handle_compare_cities(self, chat_id: int, city_1: str, city_2: str) -> None:
        self.bot.send_chat_action(chat_id, "typing")
        coords_1 = self.weather.get_coordinates(city_1)
        coords_2 = self.weather.get_coordinates(city_2)

        if not coords_1 or not coords_2:
            self.bot.send_message(chat_id, "Один из городов не найден. Попробуйте снова.")
            return

        w1 = self.weather.get_current_weather(*coords_1)
        w2 = self.weather.get_current_weather(*coords_2)

        if not w1 or not w2:
            self.bot.send_message(chat_id, self.weather.last_error or "Не удалось сравнить города.")
            return

        t1 = w1.get("main", {}).get("temp", "—")
        t2 = w2.get("main", {}).get("temp", "—")
        
        # Получаем состояние погоды
        weather1 = w1.get("weather", [{}])
        weather2 = w2.get("weather", [{}])
        raw_desc1 = weather1[0].get("description", "нет данных") if weather1 else "нет данных"
        raw_desc2 = weather2[0].get("description", "нет данных") if weather2 else "нет данных"
        desc1 = self._translate_weather_description(raw_desc1).capitalize()
        desc2 = self._translate_weather_description(raw_desc2).capitalize()

        msg = (
            f"<b>Сравнение городов</b>\n\n"
            f"<b>{city_1}</b>\n"
            f"🌡 Температура: {t1}°C\n"
            f"☁️ Состояние: {desc1}\n\n"
            f"<b>{city_2}</b>\n"
            f"🌡 Температура: {t2}°C\n"
            f"☁️ Состояние: {desc2}"
        )
        self.bot.send_message(chat_id, msg)

    def _handle_extended_by_city(self, message: types.Message, city: str) -> None:
        self.bot.send_chat_action(message.chat.id, "typing")
        coords = self.weather.get_coordinates(city)
        if not coords:
            self.bot.send_message(message.chat.id, "Город не найден.")
            return
        self._send_extended_data(message.chat.id, coords[0], coords[1], city=city)
        self.user_states[message.from_user.id] = {}

    def _evaluate_air_component(self, component: str, value: float) -> tuple[str, str]:
        """
        Оценивает компонент качества воздуха.
        Возвращает кортеж (оценка, описание).
        Оценки: "✅ Норма", "⚠️ Умеренно", "❌ Плохо"
        """
        if component == "pm2_5":
            if value < 12:
                return "✅ Норма", "в пределах нормы ВОЗ"
            elif value < 35:
                return "⚠️ Умеренно", "превышение нормы"
            else:
                return "❌ Плохо", "значительное превышение нормы"
        
        elif component == "pm10":
            if value < 20:
                return "✅ Норма", "в пределах нормы ВОЗ"
            elif value < 50:
                return "⚠️ Умеренно", "превышение нормы"
            else:
                return "❌ Плохо", "значительное превышение нормы"
        
        elif component == "no2":
            if value < 40:
                return "✅ Норма", "в пределах нормы"
            elif value < 100:
                return "⚠️ Умеренно", "превышение нормы"
            else:
                return "❌ Плохо", "значительное превышение нормы"
        
        elif component == "o3":
            if value < 60:
                return "✅ Норма", "в пределах нормы"
            elif value < 120:
                return "⚠️ Умеренно", "превышение нормы"
            else:
                return "❌ Плохо", "значительное превышение нормы"
        
        return "—", "нет данных"

    def _send_extended_data(self, chat_id: int, lat: float, lon: float, city: str | None = None) -> None:
        self.bot.send_chat_action(chat_id, "typing")
        weather = self.weather.get_current_weather(lat, lon)
        air = self.weather.get_air_pollution(lat, lon)
        if not weather:
            self.bot.send_message(chat_id, self.weather.last_error or "Не удалось получить расширенные данные.")
            return

        analysis = self.air_analyzer.analyze_air_pollution(air, extended=True)
        city_name = city or weather.get("name", "Неизвестный город")
        temp = weather.get("main", {}).get("temp", "—")
        raw_desc = weather.get("weather", [{}])[0].get("description") or "нет описания"
        desc = self._translate_weather_description(raw_desc).capitalize()

        details = analysis.get("details", {})
        
        # Формируем человекочитаемое описание компонентов качества воздуха
        air_details_lines = []
        if details:
            pm25 = float(details.get('pm2_5', 0))
            pm10 = float(details.get('pm10', 0))
            no2 = float(details.get('no2', 0))
            o3 = float(details.get('o3', 0))
            
            eval_pm25, _ = self._evaluate_air_component("pm2_5", pm25)
            air_details_lines.append(f"• Мелкие частицы PM2.5: {pm25:.2f} мкг/м³ - {eval_pm25}")
            
            eval_pm10, _ = self._evaluate_air_component("pm10", pm10)
            air_details_lines.append(f"• Крупные частицы PM10: {pm10:.2f} мкг/м³ - {eval_pm10}")
            
            eval_no2, _ = self._evaluate_air_component("no2", no2)
            air_details_lines.append(f"• Диоксид азота (NO₂): {no2:.2f} мкг/м³ - {eval_no2}")
            
            eval_o3, _ = self._evaluate_air_component("o3", o3)
            air_details_lines.append(f"• Озон (O₃): {o3:.2f} мкг/м³ - {eval_o3}")
        
        air_details_str = "\n".join(air_details_lines) if air_details_lines else "Данные о компонентах недоступны"
        
        msg = (
            f"<b>Расширенные данные: {city_name}</b>\n"
            f"🌡 Температура: {temp}°C\n"
            f"☁️ Погода: {desc}\n\n"
            f"<b>Качество воздуха</b>\n"
            f"Статус: {analysis.get('status', 'Нет данных')}\n"
            f"{analysis.get('summary', '')}\n\n"
            f"<b>Детали загрязнения:</b>\n"
            f"{air_details_str}"
        )
        self.bot.send_message(chat_id, msg)

    def _show_notifications_menu(self, chat_id: int, user_id: int) -> None:
        user_data = self.storage.load_user(user_id)
        notifications = user_data.get("notifications") or {}
        enabled = bool(notifications.get("enabled", False))
        interval_h = int(notifications.get("interval_h", self.default_interval_h))

        markup = types.InlineKeyboardMarkup(row_width=2)
        toggle_text = "Выключить" if enabled else "Включить"
        markup.add(types.InlineKeyboardButton(toggle_text, callback_data="notif_toggle"))
        for h in [1, 2, 3, 6]:
            markup.add(types.InlineKeyboardButton(f"{h} ч", callback_data=f"notif_interval|{h}"))

        text = (
            "<b>Уведомления</b>\n"
            f"Статус: {'включены' if enabled else 'выключены'}\n"
            f"Интервал: {interval_h} ч"
        )
        self.bot.send_message(chat_id, text, reply_markup=markup)

    def _handle_callback(self, call: types.CallbackQuery) -> None:
        data = call.data or ""
        user_id = call.from_user.id
        chat_id = call.message.chat.id if call.message else call.from_user.id

        if data.startswith("forecast_day|"):
            day = data.split("|", 1)[1]
            self.bot.answer_callback_query(call.id, "Загружаю прогноз...")
            self._send_forecast_day(chat_id, user_id, day)
            return

        if data == "forecast_back":
            self._send_main_menu(chat_id, "Возвращаю в главное меню.")
            self.bot.answer_callback_query(call.id)
            return

        if data == "notif_toggle":
            self._toggle_notifications(user_id)
            self._show_notifications_menu(chat_id, user_id)
            self.bot.answer_callback_query(call.id, "Статус уведомлений изменен.")
            return

        if data.startswith("notif_interval|"):
            interval = int(data.split("|", 1)[1])
            self._set_notification_interval(user_id, interval)
            self._show_notifications_menu(chat_id, user_id)
            self.bot.answer_callback_query(call.id, "Интервал обновлен.")
            return

        self.bot.answer_callback_query(call.id)

    def _handle_inline_query(self, query: types.InlineQuery) -> None:
        """Обработчик inline-запросов для поиска погоды по городу."""
        try:
            query_text = (query.query or "").strip()
            
            if not query_text or len(query_text) < 2:
                # Если запрос слишком короткий, показываем подсказку
                results = [
                    types.InlineQueryResultArticle(
                        id="hint",
                        title="Введите название города",
                        description="Начните вводить название города для поиска погоды",
                        input_message_content=types.InputTextMessageContent(
                            message_text="Введите название города (минимум 2 символа)"
                        ),
                    )
                ]
                self.bot.answer_inline_query(query.id, results, cache_time=1)
                return
            
            # Ищем координаты города
            coords = self.weather.get_coordinates(query_text, limit=1)
            
            if not coords:
                # Если город не найден
                results = [
                    types.InlineQueryResultArticle(
                        id="not_found",
                        title="Город не найден",
                        description=f"Попробуйте другой запрос: {query_text}",
                        input_message_content=types.InputTextMessageContent(
                            message_text=f"Город '{query_text}' не найден. Попробуйте другое название."
                        ),
                    )
                ]
                self.bot.answer_inline_query(query.id, results, cache_time=1)
                return
            
            # Получаем погоду для найденного города
            lat, lon = coords
            weather = self.weather.get_current_weather(lat, lon)
            
            if not weather:
                results = [
                    types.InlineQueryResultArticle(
                        id="error",
                        title="Ошибка получения данных",
                        description="Не удалось получить данные о погоде",
                        input_message_content=types.InputTextMessageContent(
                            message_text="Не удалось получить данные о погоде. Попробуйте позже."
                        ),
                    )
                ]
                self.bot.answer_inline_query(query.id, results, cache_time=1)
                return
            
            # Формируем карточку с погодой
            city_name = weather.get("name", query_text)
            main = weather.get("main", {})
            weather_meta = weather.get("weather", [{}])
            raw_desc = weather_meta[0].get("description") or "нет описания"
            description = self._translate_weather_description(raw_desc).capitalize()
            temp = main.get("temp", "—")
            
            # Формируем текст сообщения
            message_text = (
                f"<b>Погода в {city_name}</b>\n"
                f"🌡 {temp}°C\n"
                f"☁️ {description}"
            )
            
            # Создаем результат inline-запроса
            # ID должен быть уникальным строковым идентификатором (до 64 символов)
            result_id = f"weather_{city_name}_{lat:.2f}_{lon:.2f}".replace(" ", "_")[:64]
            results = [
                types.InlineQueryResultArticle(
                    id=result_id,
                    title=f"Погода в {city_name}",
                    description=f"{temp}°C, {description}",
                    input_message_content=types.InputTextMessageContent(
                        message_text=message_text,
                        parse_mode="HTML",
                    ),
                )
            ]
            
            self.bot.answer_inline_query(query.id, results, cache_time=300)
        except Exception as e:
            # В случае ошибки отправляем сообщение об ошибке
            try:
                results = [
                    types.InlineQueryResultArticle(
                        id="error_exception",
                        title="Ошибка обработки запроса",
                        description=str(e)[:50],
                        input_message_content=types.InputTextMessageContent(
                            message_text="Произошла ошибка при обработке запроса. Попробуйте позже."
                        ),
                    )
                ]
                self.bot.answer_inline_query(query.id, results, cache_time=1)
            except:
                pass  # Если даже это не сработало, просто игнорируем

    def _send_forecast_day(self, chat_id: int, user_id: int, day: str) -> None:
        self.bot.send_chat_action(chat_id, "typing")
        grouped = self.forecast_cache.get(user_id, {})
        items = grouped.get(day, [])
        if not items:
            self.bot.send_message(chat_id, "Нет данных прогноза для выбранного дня.")
            return

        lines = [f"<b>Детальный прогноз на {self._format_day_label(day)}</b>\n"]
        for item in items:
            dt_txt = item.get("dt_txt", "")
            time_str = dt_txt.split(" ")[1][:5] if " " in str(dt_txt) else "??:??"
            temp = item.get("main", {}).get("temp", "—")
            weather_list = item.get("weather", [{}])
            weather_code = weather_list[0].get("id", 800) if weather_list else 800
            raw_desc = weather_list[0].get("description", "нет описания") if weather_list else "нет описания"
            desc = self._translate_weather_description(raw_desc).capitalize()
            emoji = self._get_weather_emoji(weather_code)
            lines.append(f"{emoji} {time_str}: {temp}°C - {desc}")

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Назад", callback_data="forecast_back"))
        self.bot.send_message(chat_id, "\n".join(lines), reply_markup=markup)

    def _toggle_notifications(self, user_id: int) -> None:
        user_data = self.storage.load_user(user_id)
        notif = user_data.get("notifications", {})
        enabled = bool(notif.get("enabled", False))
        notif["enabled"] = not enabled
        notif["interval_h"] = int(notif.get("interval_h", self.default_interval_h))
        user_data["notifications"] = notif
        self.storage.save_user(user_id, user_data)

    def _set_notification_interval(self, user_id: int, interval_h: int) -> None:
        user_data = self.storage.load_user(user_id)
        notif = user_data.get("notifications", {})
        notif["enabled"] = bool(notif.get("enabled", False))
        notif["interval_h"] = max(1, interval_h)
        user_data["notifications"] = notif
        self.storage.save_user(user_id, user_data)

    def _check_notifications(self, user_id: int, chat_id: int) -> None:
        user_data = self.storage.load_user(user_id)
        notif = user_data.get("notifications", {})
        if not bool(notif.get("enabled", False)):
            return

        interval_h = int(notif.get("interval_h", self.default_interval_h))
        last_sent = float(notif.get("last_sent_ts", 0))
        now = time.time()
        if now - last_sent < interval_h * 3600:
            return

        lat = user_data.get("lat")
        lon = user_data.get("lon")
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            return

        weather = self.weather.get_current_weather(float(lat), float(lon))
        if not weather:
            return

        city = user_data.get("city") or weather.get("name", "вашей локации")
        temp = weather.get("main", {}).get("temp", "—")
        raw_desc = weather.get("weather", [{}])[0].get("description", "нет описания")
        desc = self._translate_weather_description(raw_desc).capitalize()
        self.bot.send_message(
            chat_id,
            f"🔔 Напоминание о погоде: {city}\n"
            f"Сейчас {temp}°C, {desc}",
        )

        notif["last_sent_ts"] = now
        user_data["notifications"] = notif
        self.storage.save_user(user_id, user_data)


if __name__ == "__main__":
    app = TelegramWeatherBot()
    app.run()
