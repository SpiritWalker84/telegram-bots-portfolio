import asyncio
import os
import re
from datetime import datetime, timedelta
from typing import Optional

import aiosqlite
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv

# Загружаем переменные окружения
import sys
import io

# Устанавливаем UTF-8 для вывода в консоль Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    load_dotenv(encoding='utf-8')
except Exception as e:
    print(f"Предупреждение: ошибка при загрузке .env файла: {e}")

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN or BOT_TOKEN == "your_bot_token_here":
    raise ValueError(
        "BOT_TOKEN не найден в .env файле!\n"
        "Создайте файл .env и добавьте в него:\n"
        "BOT_TOKEN=ваш_токен_от_BotFather"
    )

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DB_NAME = "tasks.db"


# Инициализация базы данных
async def init_db():
    """Создаёт таблицы tasks и user_settings, если их нет"""
    async with aiosqlite.connect(DB_NAME) as db:
        # Таблица задач
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                datetime TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME
            )
        """)
        
        # Таблица настроек пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                auto_delete_days INTEGER DEFAULT 1
            )
        """)
        
        # Добавляем поле completed_at, если его нет (для существующих баз)
        try:
            await db.execute("ALTER TABLE tasks ADD COLUMN completed_at DATETIME")
        except aiosqlite.OperationalError:
            pass  # Поле уже существует
        
        await db.commit()


# Работа с базой данных
async def add_task(user_id: int, text: str, reminder_time: Optional[datetime] = None) -> int:
    """Добавляет задачу в базу данных. Возвращает ID задачи."""
    if reminder_time is None:
        # Если время не указано, напоминание через 1 час
        reminder_time = datetime.now() + timedelta(hours=1)
    
    dt_str = reminder_time.isoformat()
    
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT INTO tasks (user_id, text, datetime, status) VALUES (?, ?, ?, ?)",
            (user_id, text, dt_str, "pending")
        )
        await db.commit()
        return cursor.lastrowid


async def get_user_tasks(user_id: int, status: Optional[str] = None) -> list:
    """Получает задачи пользователя. Если status указан, фильтрует по статусу."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        
        if status:
            cursor = await db.execute(
                "SELECT * FROM tasks WHERE user_id = ? AND status = ? ORDER BY datetime ASC",
                (user_id, status)
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM tasks WHERE user_id = ? ORDER BY datetime ASC",
                (user_id,)
            )
        
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def mark_task_done(task_id: int, user_id: int) -> bool:
    """Отмечает задачу как выполненную. Возвращает True, если задача найдена."""
    now_str = datetime.now().isoformat()
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "UPDATE tasks SET status = 'done', completed_at = ? WHERE id = ? AND user_id = ?",
            (now_str, task_id, user_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def delete_task(task_id: int, user_id: int) -> bool:
    """Удаляет задачу. Возвращает True, если задача найдена."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "DELETE FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, user_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_user_setting(user_id: int, setting_name: str, default_value):
    """Получает настройку пользователя. Если не найдена, возвращает значение по умолчанию."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            f"SELECT {setting_name} FROM user_settings WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        if row:
            return row[0]
        return default_value


async def set_user_setting(user_id: int, setting_name: str, value):
    """Устанавливает настройку пользователя."""
    async with aiosqlite.connect(DB_NAME) as db:
        # Проверяем, существует ли запись
        cursor = await db.execute(
            "SELECT user_id FROM user_settings WHERE user_id = ?",
            (user_id,)
        )
        exists = await cursor.fetchone()
        
        if exists:
            # Обновляем существующую запись
            await db.execute(
                f"UPDATE user_settings SET {setting_name} = ? WHERE user_id = ?",
                (value, user_id)
            )
        else:
            # Создаём новую запись (с дефолтным значением для другого поля)
            await db.execute(
                f"INSERT INTO user_settings (user_id, {setting_name}) VALUES (?, ?)",
                (user_id, value)
            )
        await db.commit()


async def get_pending_tasks_for_reminder() -> list:
    """Получает все задачи со статусом 'pending', время которых уже наступило."""
    now = datetime.now()
    now_str = now.isoformat()
    
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM tasks WHERE status = 'pending' AND datetime <= ?",
            (now_str,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def remove_expired_tasks():
    """Удаляет истёкшие задачи с учётом индивидуальных настроек пользователей"""
    now = datetime.now()
    
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        
        # Получаем все выполненные задачи
        cursor = await db.execute(
            "SELECT id, user_id, completed_at FROM tasks WHERE status = 'done' AND completed_at IS NOT NULL"
        )
        done_tasks = await cursor.fetchall()
        
        # Удаляем выполненные задачи, которые истекли по настройкам пользователя
        for task in done_tasks:
            user_id = task["user_id"]
            completed_at_str = task["completed_at"]
            
            try:
                completed_at = datetime.fromisoformat(completed_at_str)
                auto_delete_days = await get_user_setting(user_id, "auto_delete_days", 1)
                expired_time = completed_at + timedelta(days=auto_delete_days)
                
                if now >= expired_time:
                    await db.execute("DELETE FROM tasks WHERE id = ?", (task["id"],))
            except (ValueError, TypeError):
                # Если дата в неверном формате, пропускаем
                continue
        
        # Удаляем просроченные задачи (более 24 часов с момента напоминания)
        expired_time = now - timedelta(hours=24)
        expired_str = expired_time.isoformat()
        await db.execute(
            "DELETE FROM tasks WHERE status = 'pending' AND datetime < ?",
            (expired_str,)
        )
        
        await db.commit()


async def send_reminders():
    """Отправляет напоминания пользователям о задачах, время которых наступило"""
    tasks = await get_pending_tasks_for_reminder()
    
    for task in tasks:
        user_id = task["user_id"]
        task_text = task["text"]
        task_id = task["id"]
        
        try:
            message = f"🔔 Напоминание!\n\nЗадача #{task_id}: {task_text}"
            await bot.send_message(chat_id=user_id, text=message)
            
            # Отмечаем задачу как выполненную после отправки напоминания
            await mark_task_done(task_id, user_id)
        except Exception as e:
            print(f"Ошибка при отправке напоминания пользователю {user_id}: {e}")


async def reminder_loop():
    """Фоновый цикл для проверки и отправки напоминаний"""
    while True:
        try:
            await send_reminders()
            await remove_expired_tasks()
        except Exception as e:
            print(f"Ошибка в reminder_loop: {e}")
        
        await asyncio.sleep(60)  # Проверка каждые 60 секунд


# Обработчики команд
@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    welcome_text = """
👋 Привет! Я бот-напоминатель задач.

📋 Доступные команды:
/add <текст задачи> [время] — добавить задачу с напоминанием
/list — показать все ваши задачи
/done <id> — отметить задачу как выполненную
/delete <id> или /del <id> — удалить задачу
/settings — настройки (автоудаление выполненных задач)

Примеры:
/add Купить молоко в 14:30
/add Встреча в 2025-12-26 15:00
/add Оплатить счёт завтра 18:00
/add Позвонить маме
/list
/done 1
"""
    await message.answer(welcome_text)


@dp.message(Command("add"))
async def cmd_add(message: Message):
    """Обработчик команды /add <текст> [время/дата]"""
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.answer(
            "❌ Использование: /add <текст задачи> [время]\n\n"
            "Примеры:\n"
            "/add Купить молоко в 14:30\n"
            "/add Встреча в 2025-12-26 15:00\n"
            "/add Оплатить счёт завтра 18:00"
        )
        return
    
    text_with_time = args[1]
    reminder_time = None
    task_text = text_with_time
    now = datetime.now()
    
    # 1. Парсинг формата: "в 2025-12-26 15:00" или "2025-12-26 15:00"
    date_time_pattern = r'(?:в\s+)?(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{2})'
    match = re.search(date_time_pattern, text_with_time)
    
    if match:
        try:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            hours = int(match.group(4))
            minutes = int(match.group(5))
            
            if not (1 <= month <= 12 and 1 <= day <= 31 and 0 <= hours <= 23 and 0 <= minutes <= 59):
                raise ValueError("Неверный формат даты/времени")
            
            reminder_time = datetime(year, month, day, hours, minutes, 0)
            
            # Удаляем дату и время из текста задачи
            task_text = re.sub(date_time_pattern, '', text_with_time, flags=re.IGNORECASE).strip()
            task_text = re.sub(r'\s+', ' ', task_text)
            
        except (ValueError, AttributeError):
            await message.answer("❌ Неверный формат даты. Используйте: YYYY-MM-DD HH:MM (например, 2025-12-26 15:00)")
            return
    
    # 2. Парсинг формата: "завтра HH:MM" или "завтра в HH:MM"
    if not reminder_time:
        tomorrow_pattern = r'завтра\s+(?:в\s+)?(\d{1,2}):(\d{2})'
        match = re.search(tomorrow_pattern, text_with_time, re.IGNORECASE)
        
        if match:
            try:
                hours = int(match.group(1))
                minutes = int(match.group(2))
                
                if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
                    raise ValueError("Неверный формат времени")
                
                # Устанавливаем на завтра
                reminder_time = (now + timedelta(days=1)).replace(hour=hours, minute=minutes, second=0, microsecond=0)
                
                # Удаляем "завтра" и время из текста задачи
                task_text = re.sub(tomorrow_pattern, '', text_with_time, flags=re.IGNORECASE).strip()
                task_text = re.sub(r'\s+', ' ', task_text)
                
            except (ValueError, AttributeError):
                await message.answer("❌ Неверный формат времени. Используйте: завтра HH:MM (например, завтра 18:00)")
                return
    
    # 3. Парсинг формата: "в HH:MM" или просто "HH:MM" (сегодня)
    if not reminder_time:
        time_pattern = r'в\s+(\d{1,2}):(\d{2})|^(\d{1,2}):(\d{2})$'
        match = re.search(time_pattern, text_with_time, re.IGNORECASE)
        
        if match:
            try:
                hours = int(match.group(1) or match.group(3))
                minutes = int(match.group(2) or match.group(4))
                
                if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
                    raise ValueError("Неверный формат времени")
                
                # Устанавливаем время на сегодня
                reminder_time = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
                
                # Если время уже прошло сегодня, устанавливаем на завтра
                if reminder_time <= now:
                    reminder_time += timedelta(days=1)
                
                # Удаляем время из текста задачи
                task_text = re.sub(time_pattern, '', text_with_time, flags=re.IGNORECASE).strip()
                task_text = re.sub(r'\s+', ' ', task_text)
                
            except (ValueError, AttributeError):
                await message.answer("❌ Неверный формат времени. Используйте: HH:MM (например, 18:30)")
                return
    
    # Очистка текста задачи
    if not task_text:
        task_text = "Задача без описания"
    
    try:
        task_id = await add_task(message.from_user.id, task_text, reminder_time)
        
        if reminder_time:
            time_str = reminder_time.strftime("%d.%m.%Y в %H:%M")
            response = f"✅ Задача #{task_id} добавлена!\n\n📝 {task_text}\n⏰ Напоминание: {time_str}"
        else:
            response = f"✅ Задача #{task_id} добавлена!\n\n📝 {task_text}\n⏰ Напоминание через 1 час"
        
        await message.answer(response)
    except Exception as e:
        await message.answer(f"❌ Ошибка при добавлении задачи: {e}")


@dp.message(Command("list"))
async def cmd_list(message: Message):
    """Обработчик команды /list"""
    tasks = await get_user_tasks(message.from_user.id)
    
    if not tasks:
        await message.answer("📋 У вас пока нет задач. Добавьте задачу командой /add")
        return
    
    pending_tasks = [t for t in tasks if t["status"] == "pending"]
    done_tasks = [t for t in tasks if t["status"] == "done"]
    
    response = "📋 Ваши задачи:\n\n"
    
    if pending_tasks:
        response += "⏳ Активные задачи:\n"
        for task in pending_tasks:
            task_id = task["id"]
            task_text = task["text"]
            try:
                task_dt = datetime.fromisoformat(task["datetime"])
                dt_str = task_dt.strftime("%d.%m.%Y в %H:%M")
                response += f"  #{task_id} — {task_text} (⏰ {dt_str})\n"
            except:
                response += f"  #{task_id} — {task_text}\n"
        response += "\n"
    
    if done_tasks:
        response += "✅ Выполненные задачи:\n"
        for task in done_tasks[:10]:  # Показываем только последние 10
            task_id = task["id"]
            task_text = task["text"]
            response += f"  #{task_id} — {task_text}\n"
    
    await message.answer(response)


@dp.message(Command("done"))
async def cmd_done(message: Message):
    """Обработчик команды /done <id>"""
    args = message.text.split()
    
    if len(args) < 2:
        await message.answer("❌ Использование: /done <id>\n\nПример: /done 1")
        return
    
    try:
        task_id = int(args[1])
    except ValueError:
        await message.answer("❌ ID задачи должен быть числом")
        return
    
    success = await mark_task_done(task_id, message.from_user.id)
    
    if success:
        await message.answer(f"✅ Задача #{task_id} отмечена как выполненная!")
    else:
        await message.answer(f"❌ Задача #{task_id} не найдена или уже выполнена")


@dp.message(Command("delete", "del"))
async def cmd_delete(message: Message):
    """Обработчик команды /delete <id> или /del <id>"""
    args = message.text.split()
    
    if len(args) < 2:
        await message.answer("❌ Использование: /delete <id> или /del <id>\n\nПример: /delete 1")
        return
    
    try:
        task_id = int(args[1])
    except ValueError:
        await message.answer("❌ ID задачи должен быть числом")
        return
    
    success = await delete_task(task_id, message.from_user.id)
    
    if success:
        await message.answer(f"🗑️ Задача #{task_id} удалена!")
    else:
        await message.answer(f"❌ Задача #{task_id} не найдена")


@dp.message(Command("settings", "set"))
async def cmd_settings(message: Message):
    """Обработчик команды /settings"""
    args = message.text.split()
    
    if len(args) < 2:
        # Показываем текущие настройки
        auto_delete_days = await get_user_setting(message.from_user.id, "auto_delete_days", 1)
        response = (
            f"⚙️ Ваши настройки:\n\n"
            f"🗑️ Автоудаление выполненных задач: через {auto_delete_days} дн."
            f"{' (по умолчанию)' if auto_delete_days == 1 else ''}\n\n"
            f"📝 Изменить настройки:\n"
            f"/settings auto_delete <дни>\n\n"
            f"Пример: /settings auto_delete 7\n"
            f"(выполненные задачи будут удаляться через 7 дней)"
        )
        await message.answer(response)
        return
    
    if args[1].lower() == "auto_delete":
        if len(args) < 3:
            await message.answer("❌ Использование: /settings auto_delete <дни>\n\nПример: /settings auto_delete 7")
            return
        
        try:
            days = int(args[2])
            if days < 0:
                await message.answer("❌ Количество дней не может быть отрицательным")
                return
            if days > 365:
                await message.answer("❌ Максимальное значение: 365 дней")
                return
            
            await set_user_setting(message.from_user.id, "auto_delete_days", days)
            
            if days == 0:
                await message.answer("✅ Автоудаление выполненных задач отключено")
            else:
                await message.answer(f"✅ Автоудаление выполненных задач установлено: через {days} дн.")
        except ValueError:
            await message.answer("❌ Количество дней должно быть числом")
    else:
        await message.answer("❌ Неизвестная настройка. Доступно: auto_delete")


async def main():
    """Главная функция запуска бота"""
    # Инициализация базы данных
    await init_db()
    print("✅ База данных инициализирована")
    
    # Запуск фонового цикла для напоминаний
    reminder_task = asyncio.create_task(reminder_loop())
    print("✅ Цикл напоминаний запущен")
    
    try:
        # Проверка подключения
        bot_info = await bot.get_me()
        print(f"✅ Бот подключён: @{bot_info.username} ({bot_info.first_name})")
        
        # Запуск бота
        print("🚀 Бот запущен и ожидает сообщения...")
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
        import traceback
        traceback.print_exc()
    except KeyboardInterrupt:
        print("\n⏹️  Остановка бота...")
    finally:
        # Отмена фоновой задачи
        reminder_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            pass
        
        # Закрытие сессии бота
        await bot.session.close()
        print("✅ Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 До свидания!")

