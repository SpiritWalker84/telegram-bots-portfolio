# Weather Telegram Bot

Telegram-бот для получения данных о погоде через OpenWeather API.

**Бот LIVE:** [@spiritweather_bot](https://t.me/spiritweather_bot)  
**Inline-режим:** работает — поиск погоды по городу через `@spiritweather_bot Москва`

## Архитектура

- **bot.py** — основной класс `TelegramWeatherBot`, обработчики команд и inline-запросов
- **weather_app.py** — клиент OpenWeather API (`WeatherClient`), кэширование (`OpenWeatherCache`), анализ качества воздуха (`AirQualityAnalyzer`)
- **storage.py** — thread-safe хранилище пользовательских данных в JSON (`UserStorage`)

## Зависимости

- `requests` — HTTP-запросы к OpenWeather API
- `python-dotenv` — загрузка переменных окружения из `.env`
- `pyTelegramBotAPI` — Telegram Bot API

## Конфигурация

Переменные окружения (`.env`):
- `BOT_TOKEN` — токен Telegram-бота
- `OW_API_KEY` — API ключ OpenWeather
- `REQUEST_TIMEOUT` — таймаут HTTP-запросов (по умолчанию: 8)
- `CACHE_TTL_MIN` — время жизни кэша в минутах (по умолчанию: 10)
- `DEFAULT_NOTIFICATIONS_INTERVAL_H` — интервал уведомлений по умолчанию в часах (по умолчанию: 2)

## Структура данных

### User_Data.json
```json
{
  "user_id": {
    "city": "string",
    "lat": float,
    "lon": float,
    "notifications": {
      "enabled": bool,
      "interval_h": int,
      "last_sent_ts": float
    }
  }
}
```

## Особенности реализации

- Кэширование ответов OpenWeather API в `.cache/*.json` (TTL: 10 минут)
- Retry-логика для обработки rate limit (429) с экспоненциальной задержкой
- Thread-safe операции с JSON-хранилищем через `threading.Lock`
- Fallback-перевод описаний погоды с английского на русский
- Inline-режим для поиска погоды по городу
- Обработка геолокации пользователя
- Система уведомлений с проверкой по времени при входящих апдейтах
