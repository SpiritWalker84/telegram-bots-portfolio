import asyncio
import logging
import re
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from dotenv import load_dotenv
import os
import json

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Примечание: site_chat_id извлекается из текста сообщений, отправляемых Flask сервером

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("Бот для сайта готов! Жду сообщений с сайта.")

@dp.message(F.chat.id == ADMIN_CHAT_ID)
async def admin_message(message: types.Message):
    if message.reply_to_message:
        # Получаем site_chat_id из текста сообщения
        site_chat_id = None
        if message.reply_to_message.text:
            # Пытаемся извлечь chat_id из текста сообщения
            # Ищем паттерн вида "chat_id: chat_xxx" и захватываем только ID (до скобки, новой строки или конца строки)
            match = re.search(r'chat_id:\s*([a-zA-Z0-9_]+)', message.reply_to_message.text)
            if match:
                site_chat_id = match.group(1)
                print(f"[BOT] Извлечен site_chat_id: {site_chat_id} из текста: {message.reply_to_message.text[:100]}")
            else:
                print(f"[BOT] Не удалось извлечь chat_id из: {message.reply_to_message.text[:100]}")
        
        if site_chat_id:
            # Это ответ на сообщение с сайта - отправляем обратно через Flask
            try:
                print(f"[BOT] Отправка ответа на Flask: chat_id={site_chat_id}, message={message.text}")
                response = requests.post('http://localhost:5000/admin_reply', json={
                    'site_chat_id': site_chat_id,
                    'message': message.text
                }, timeout=5)
                print(f"[BOT] Ответ Flask: {response.status_code}, {response.text}")
                if response.status_code == 200:
                    await message.answer("✅ Ответ отправлен на сайт")
                else:
                    await message.answer(f"⚠️ Ошибка отправки: {response.status_code}")
            except Exception as e:
                print(f"[BOT] Ошибка при отправке на Flask: {e}")
                await message.answer(f"⚠️ Не удалось отправить ответ на сайт: {str(e)}")
        else:
            await message.answer("❌ Не найден site_chat_id в сообщении. Ответьте на сообщение с сайта (которое содержит chat_id).")
    else:
        await message.answer("💡 Ответьте на сообщение от сайта (reply), чтобы отправить ответ.")

# Этот handler больше не используется, так как сообщения идут через Flask сервер
# Оставлен для совместимости
@dp.message()
async def site_message(message: types.Message):
    # Игнорируем сообщения, которые не от админа (они обрабатываются через Flask)
    pass

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
