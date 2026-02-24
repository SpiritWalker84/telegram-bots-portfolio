# 🤖 Telegram Bots Portfolio

> **Telegram Bots Portfolio (Production-ready)**
> 
> 2 production-бота развернуты на Ubuntu VPS + systemd  
> **Live demo:** [@brooking_bbot](https://t.me/brooking_bbot) | [@reminderdemo_bot](https://t.me/reminderdemo_bot)
> 
> [![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04-orange?logo=ubuntu)](https://ubuntu.com)
> [![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
> [![systemd](https://img.shields.io/badge/systemd-service-green?logo=linux)](https://systemd.io)
> [![GitHub](https://img.shields.io/badge/GitHub-Portfolio-black?logo=github)](https://github.com/SpiritWalker84/telegram-bots-portfolio)

## ✨ Демонстрация проектов

| Бот | Функционал | Стек | Статус |
|-----|------------|------|--------|
| **Booking Bot** | Бронирование услуг салона красоты<br>Календарь, базы данных, админ-панель | aiogram 3.x • SQLite • FSM • Pydantic | 🟢 **LIVE** [@brooking_bbot](https://t.me/brooking_bbot) |
| **Reminder Bot** | Напоминания с планировщиком<br>Расписание, уведомления | aiogram 3.x • SQLite • asyncio | 🟢 **LIVE** [@reminderdemo_bot](https://t.me/reminderdemo_bot) |
| **Weather Bot** | Погода по городу, OpenWeather API<br>Inline-режим, уведомления, качество воздуха | pyTelegramBotAPI • requests • кэш | 🟢 **LIVE** [@spiritweather_bot](https://t.me/spiritweather_bot) |

## 🛠 Стек технологий

- **🐍 Python 3.11+** • **aiogram 3.x** • **asyncio**
- **🗄️ SQLite3** • **aiosqlite** (асинхронная работа с БД)
- **⚙️ Pydantic Settings** (конфигурация)
- **🐧 Ubuntu 24.04** + **systemd services**
- **📦 Git** • **GitHub** (версионирование)
- **🔧 SSH** • **production deploy**

## 🚀 Быстрый старт (5 минут)

```bash
git clone https://github.com/SpiritWalker84/telegram-bots-portfolio
cd telegram-bots-portfolio/booking-bot
./run.sh  # автоматическая установка и запуск
```

---

## ✅ Опыт в продакшене

- ✅ **2 бота 24/7 на VPS** — работают в продакшене
- ✅ **Full-stack** — Python backend + Linux DevOps
- ✅ **Live демо** — боты работают прямо сейчас
- ✅ **Clean code** — модульная архитектура, документация
- ✅ **Freelance-ready** — готов к коммерческим задачам

---

Коллекция Telegram-ботов на Python, созданных для демонстрации различных возможностей и технологий.

## 📸 Скриншоты

> 💡 **Примечание:** Скриншоты и демонстрации работы ботов находятся в README каждого проекта. Перейдите в папку конкретного бота для просмотра.

## 📚 Проекты

### 1. Reminder Bot 🤖

Telegram-бот для управления задачами и напоминаниями с использованием aiogram 3.x и SQLite.

**Возможности:**

* Добавление задач с гибким парсингом времени
* Автоматические напоминания
* Управление задачами (добавление, выполнение, удаление)
* Настройка автоудаления выполненных задач

**Технологии:** Python, aiogram 3.x, SQLite, aiosqlite

**Быстрый старт:**

```bash
cd reminder-bot
pip install -r requirements.txt
cp .env.example .env
# Заполните BOT_TOKEN в .env
python main.py
```

**📸 Демонстрация:** См. скриншоты в [README проекта](reminder-bot/README.md)

---

### 2. Booking Bot 📅

Масштабируемый Telegram бот для записи на услуги, рассчитанный на 5к+ клиентов. Построен на aiogram 3.x с использованием aiosqlite для асинхронной работы с базой данных.

**Возможности:**

**Для клиентов:**
* ✅ Запись через inline-кнопки с удобным календарем
* ✅ Парсинг естественного языка - запись через текстовые сообщения ("завтра 15:00")
* ✅ Визуальное отображение времени - занятые времена помечены ❌, прошедшие ⏰
* ✅ Просмотр своих записей с возможностью отмены
* ✅ Автоматические напоминания - уведомление за 30 минут до записи
* ✅ Просмотр услуг с информацией о длительности и стоимости

**Для администраторов:**
* ✅ Админ-панель - полный контроль над ботом
* ✅ Управление услугами - добавление, редактирование, удаление (деактивация) услуг
* ✅ Просмотр записей - по датам, на сегодня, статистика
* ✅ Управление записями - подтверждение и отмена записей
* ✅ Настройка времени работы - начало и конец рабочего дня
* ✅ Настройка интервала между записями (в минутах)
* ✅ Управление администраторами
* ✅ Уведомления о новых записях с автоудалением

**Технологии:** Python, aiogram 3.x, SQLite, aiosqlite, python-dateutil

**Быстрый старт:**

```bash
cd booking-bot
pip install -r requirements.txt
cp env.example .env
# Заполните BOT_TOKEN и ADMIN_ID в .env
python main.py
```

**📸 Демонстрация:** См. скриншоты в [README проекта](booking-bot/README.md)

**Основные команды:**
- `/start` - Главное меню
- `/help` - Справка по использованию бота
- `/cancel` - Отменить текущее действие

**Особенности:**
- Визуальное отображение доступных, занятых и прошедших времен
- Умная проверка времени с учетом длительности услуги
- Автоматические напоминания за 30 минут до записи
- Graceful shutdown для корректного завершения работы
- Оптимизированные запросы с индексами для быстрой работы

---

### 3. PDF Checkmaker Bot 📄

Telegram бот для генерации PDF-чеков из файлов данных (CSV/JSON/Excel) с использованием HTML шаблонов.

**Возможности:**

* ✅ Поддержка CSV, JSON и Excel (.xlsx) файлов
* ✅ Автоматическое определение типа файла
* ✅ Поддержка различных кодировок (UTF-8, CP1251)
* ✅ Рендеринг HTML шаблонов с Jinja2
* ✅ Автоматическая защита верстки (CSS fallback)
* ✅ Обрезка длинных текстов
* ✅ Формат чека A6 с настраиваемыми отступами
* ✅ Интуитивный интерфейс Telegram бота
* ✅ Поддержка массивов объектов и одиночных объектов (JSON)

**Технологии:** Python, aiogram 3.x, WeasyPrint, Jinja2, pandas, openpyxl

**Быстрый старт:**

```bash
cd pdf-checkmaker-bot
pip install -r requirements.txt
cp .env.example .env  # если есть
# Создайте .env файл с BOT_TOKEN и ADMIN_ID (опционально)
python bot.py
```

**📸 Демонстрация:** См. скриншоты в [README проекта](pdf-checkmaker-bot/README.md)

**Использование:**
1. Отправьте команду `/start`
2. Загрузите файл с данными (CSV, JSON или Excel)
3. Загрузите HTML шаблон
4. Нажмите "Преобразовать в PDF"
5. Получите готовый PDF-чек!

**Поддерживаемые форматы:**
- **CSV:** UTF-8, CP1251, Windows-1251 (автоопределение кодировки)
- **JSON:** UTF-8 (массивы объектов и одиночные объекты)
- **Excel:** .xlsx формат

**Особенности:**
- HTML шаблоны используют Jinja2 синтаксис
- Автоматическое вычисление общей суммы
- Защита от длинных текстов с автоматической обрезкой
- Поддержка различных кодировок для CSV файлов

---

### 4. Course Payment Bot 💳

Telegram-бот на aiogram 3.x для продажи онлайн-курса с интеграцией платежей ЮKassa.

**Возможности:**

* ✅ Продажа курса через Telegram Payments
* ✅ Интеграция с ЮKassa для обработки платежей
* ✅ Автоматическое предоставление доступа к каналу после оплаты
* ✅ Управление пользователями и платежами
* ✅ База данных для отслеживания оплативших пользователей

**Технологии:** Python, aiogram 3.x, SQLite, aiosqlite, ЮKassa

**Быстрый старт:**

```bash
cd CoursePaymentBot
pip install -r requirements.txt
cp .env.example .env
# Заполните BOT_TOKEN, PROVIDER_TOKEN, CHANNEL_ID в .env
python main.py
```

**📸 Демонстрация:** См. скриншоты в [README проекта](CoursePaymentBot/README.md)

**Подробная документация:**
- `CLIENT_SETUP.md` - Инструкция для клиента по настройке
- `PAYMENT_SETUP.md` - Настройка платежей
- `CHANNEL_SETUP.md` - Настройка канала
- `PRODUCTION_SETUP.md` - Настройка для продакшена

---

### 5. Telegram Site Chat 💬

Система чата между посетителями сайта и администратором через Telegram бота. Сообщения с сайта отправляются администратору в Telegram, а ответы администратора доставляются обратно на сайт в реальном времени.

**Возможности:**

* ✅ Веб-интерфейс чата для посетителей сайта
* ✅ Интеграция с Telegram для получения сообщений администратором
* ✅ Двусторонняя связь: сообщения с сайта → Telegram, ответы → сайт
* ✅ Автоматическая доставка ответов на сайт
* ✅ Простой API для интеграции с любым сайтом
* ✅ Поддержка множественных чатов (каждый посетитель имеет свой chat_id)

**Технологии:** Python, aiogram 3.x, Flask, JavaScript, HTML/CSS

**Быстрый старт:**

```bash
cd telegram-site-chat
pip install -r requirements.txt
cp .env.example .env
# Заполните BOT_TOKEN и ADMIN_CHAT_ID в .env
# В одном терминале:
python server.py
# В другом терминале:
python bot.py
# Откройте index.html в браузере
```

**📸 Демонстрация:** См. скриншоты в [README проекта](telegram-site-chat/README.md)

**Архитектура:**
- `bot.py` - Telegram бот (aiogram), обрабатывает сообщения и ответы администратора
- `server.py` - Flask сервер, принимает сообщения с сайта и отправляет их в Telegram
- `index.html` - Веб-интерфейс чата для посетителей сайта

**Как использовать:**
1. Посетитель вводит сообщение на сайте
2. Администратор получает сообщение в Telegram с указанием `chat_id`
3. Администратор отвечает на сообщение в Telegram (reply)
4. Ответ автоматически появляется на сайте

---

### 6. Weather Bot 🌤️

Telegram-бот для получения погоды через OpenWeather API. Inline-режим, уведомления по расписанию, качество воздуха.

**Возможности:**

* Погода по городу (команды и inline: `@spiritweather_bot Москва`)
* Геолокация пользователя
* Кэширование ответов API (TTL 10 мин), retry при rate limit
* Уведомления о погоде по расписанию
* Анализ качества воздуха
* Fallback-перевод описаний на русский

**Технологии:** Python, pyTelegramBotAPI, requests, OpenWeather API, python-dotenv

**Быстрый старт:**

```bash
cd weather_bot
pip install -r requirements.txt
cp .env.example .env
# Заполните BOT_TOKEN и OW_API_KEY в .env
python bot.py
```

**📸 Демонстрация:** [@spiritweather_bot](https://t.me/spiritweather_bot) — LIVE, inline-режим работает.

---

## 🚀 Быстрый старт

Каждый бот в портфолио имеет свою папку с индивидуальными инструкциями по установке и запуску. Перейдите в папку конкретного бота для подробной информации.

## 📝 Лицензия

Проекты в этом портфолио созданы в образовательных целях. Используйте свободно для обучения и разработки.

## 👤 Автор

**SpiritWalker84**

---

_Это портфолио постоянно пополняется новыми проектами_
