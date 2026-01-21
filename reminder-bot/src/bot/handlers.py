"""Обработчики команд и сообщений бота."""
from datetime import datetime
from typing import TYPE_CHECKING

from aiogram.filters import Command
from aiogram import F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ContentType
from aiogram.exceptions import TelegramBadRequest

from src.bot.keyboards import (
    get_main_menu,
    get_task_list_keyboard,
    get_empty_tasks_keyboard,
    get_settings_keyboard
)

if TYPE_CHECKING:
    from src.services.task_service import TaskService
    from src.database.models import Database


class BotHandlers:
    """Класс с обработчиками команд бота."""
    
    def __init__(self, task_service: "TaskService", database: "Database"):
        """
        Инициализация обработчиков.
        
        Args:
            task_service: Экземпляр TaskService
            database: Экземпляр Database для работы с настройками
        """
        self.task_service = task_service
        self.db = database
    
    def register_handlers(self, dp) -> None:
        """
        Регистрирует все обработчики команд и callback в диспетчере.
        
        Args:
            dp: Экземпляр Dispatcher из aiogram
        """
        # Команды
        dp.message.register(self.cmd_start, Command("start"))
        dp.message.register(self.cmd_add, Command("add"))
        dp.message.register(self.cmd_list, Command("list"))
        dp.message.register(self.cmd_done, Command("done"))
        dp.message.register(self.cmd_delete, Command("delete", "del"))
        dp.message.register(self.cmd_settings, Command("settings", "set"))
        
        # Обработчик обычных текстовых сообщений (для добавления задач через кнопку)
        # Регистрируем в конце, чтобы команды обрабатывались первыми
        dp.message.register(self.handle_text_message, F.text)
        
        # Callback handlers для кнопок
        dp.callback_query.register(self.callback_main_menu, lambda c: c.data == "main_menu")
        dp.callback_query.register(self.callback_list_tasks, lambda c: c.data == "list_tasks")
        dp.callback_query.register(self.callback_add_task, lambda c: c.data == "add_task")
        dp.callback_query.register(self.callback_settings, lambda c: c.data == "settings")
        dp.callback_query.register(self.callback_task_done, lambda c: c.data and c.data.startswith("task_done_"))
        dp.callback_query.register(self.callback_task_delete, lambda c: c.data and c.data.startswith("task_delete_"))
        dp.callback_query.register(self.callback_task_info, lambda c: c.data and c.data.startswith("task_info_"))
        dp.callback_query.register(self.callback_settings_auto_delete, lambda c: c.data == "settings_auto_delete")
        dp.callback_query.register(self.callback_set_delete_days, lambda c: c.data and c.data.startswith("set_delete_"))
    
    async def cmd_start(self, message: Message) -> None:
        """Обработчик команды /start"""
        welcome_text = """
👋 Привет! Я бот-напоминатель задач.

Используйте кнопки ниже для управления задачами, или команды:

📋 Команды:
/add <текст> [время] — добавить задачу
/list — показать все задачи
/done <id> — отметить как выполненную
/delete <id> — удалить задачу
/settings — настройки

💡 Примеры:
/add Купить молоко в 14:30
/add Встреча в 2025-12-26 15:00
/add Оплатить счёт завтра 18:00
"""
        await message.answer(welcome_text, reply_markup=get_main_menu())
    
    async def cmd_add(self, message: Message) -> None:
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
        
        try:
            task_id = await self.task_service.add_task(
                message.from_user.id, 
                text_with_time
            )
            
            # Получаем добавленную задачу для отображения времени
            tasks = await self.task_service.get_user_tasks(message.from_user.id)
            task = next((t for t in tasks if t["id"] == task_id), None)
            
            if task:
                try:
                    task_dt = datetime.fromisoformat(task["datetime"])
                    time_str = task_dt.strftime("%d.%m.%Y в %H:%M")
                    response = (
                        f"✅ Задача #{task_id} добавлена!\n\n"
                        f"📝 {task['text']}\n"
                        f"⏰ Напоминание: {time_str}"
                    )
                except:
                    response = (
                        f"✅ Задача #{task_id} добавлена!\n\n"
                        f"📝 {task['text']}\n"
                        f"⏰ Напоминание через 1 час"
                    )
            else:
                response = f"✅ Задача #{task_id} добавлена!"
            
            await message.answer(response)
        except Exception as e:
            await message.answer(f"❌ Ошибка при добавлении задачи: {e}")
    
    async def handle_text_message(self, message: Message) -> None:
        """
        Обработчик обычных текстовых сообщений.
        Добавляет задачу, если это не команда.
        """
        # Пропускаем команды (они обрабатываются отдельно)
        if message.text and message.text.startswith('/'):
            return
        
        # Обрабатываем как задачу
        text_with_time = message.text
        
        try:
            task_id = await self.task_service.add_task(
                message.from_user.id, 
                text_with_time
            )
            
            # Получаем добавленную задачу для отображения времени
            tasks = await self.task_service.get_user_tasks(message.from_user.id)
            task = next((t for t in tasks if t["id"] == task_id), None)
            
            if task:
                try:
                    task_dt = datetime.fromisoformat(task["datetime"])
                    time_str = task_dt.strftime("%d.%m.%Y в %H:%M")
                    response = (
                        f"✅ Задача #{task_id} добавлена!\n\n"
                        f"📝 {task['text']}\n"
                        f"⏰ Напоминание: {time_str}"
                    )
                except:
                    response = (
                        f"✅ Задача #{task_id} добавлена!\n\n"
                        f"📝 {task['text']}\n"
                        f"⏰ Напоминание через 1 час"
                    )
            else:
                response = f"✅ Задача #{task_id} добавлена!"
            
            from src.bot.keyboards import get_main_menu
            await message.answer(response, reply_markup=get_main_menu())
        except Exception as e:
            await message.answer(f"❌ Ошибка при добавлении задачи: {e}")
    
    async def cmd_list(self, message: Message) -> None:
        """Обработчик команды /list"""
        await self._show_task_list(message)
    
    async def _show_task_list(self, message_or_callback) -> None:
        """Вспомогательный метод для отображения списка задач."""
        user_id = message_or_callback.from_user.id
        
        tasks = await self.task_service.get_user_tasks(user_id)
        
        if not tasks:
            text = "📋 У вас пока нет задач.\n\nИспользуйте кнопку ниже для добавления или команду /add"
            keyboard = get_empty_tasks_keyboard()
        else:
            pending_tasks = [t for t in tasks if t["status"] == "pending"]
            done_tasks = [t for t in tasks if t["status"] == "done"]
            
            text = "📋 Ваши задачи:\n\n"
            
            if pending_tasks:
                text += "⏳ Активные задачи:\n"
                for task in pending_tasks[:10]:
                    task_id = task["id"]
                    task_text = task["text"]
                    try:
                        task_dt = datetime.fromisoformat(task["datetime"])
                        dt_str = task_dt.strftime("%d.%m.%Y в %H:%M")
                        text += f"  #{task_id} — {task_text}\n  ⏰ {dt_str}\n\n"
                    except:
                        text += f"  #{task_id} — {task_text}\n\n"
            
            if done_tasks:
                text += "✅ Выполненные задачи:\n"
                for task in done_tasks[:5]:
                    task_id = task["id"]
                    task_text = task["text"]
                    text += f"  #{task_id} — {task_text}\n"
            
            keyboard = get_task_list_keyboard(pending_tasks, done_tasks)
        
        if isinstance(message_or_callback, CallbackQuery):
            try:
                await message_or_callback.message.edit_text(text, reply_markup=keyboard)
            except TelegramBadRequest as e:
                # Игнорируем ошибку, если сообщение не изменилось
                if "message is not modified" not in str(e).lower():
                    raise
            await message_or_callback.answer()
        else:
            await message_or_callback.answer(text, reply_markup=keyboard)
    
    async def cmd_done(self, message: Message) -> None:
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
        
        success = await self.task_service.mark_task_done(task_id, message.from_user.id)
        
        if success:
            await message.answer(f"✅ Задача #{task_id} отмечена как выполненная!")
        else:
            await message.answer(f"❌ Задача #{task_id} не найдена или уже выполнена")
    
    async def cmd_delete(self, message: Message) -> None:
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
        
        success = await self.task_service.delete_task(task_id, message.from_user.id)
        
        if success:
            await message.answer(f"🗑️ Задача #{task_id} удалена!")
        else:
            await message.answer(f"❌ Задача #{task_id} не найдена")
    
    async def cmd_settings(self, message: Message) -> None:
        """Обработчик команды /settings"""
        args = message.text.split()
        
        if len(args) < 2:
            # Показываем текущие настройки
            auto_delete_days = await self.db.get_user_setting(
                message.from_user.id, "auto_delete_days", 1
            )
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
                await message.answer(
                    "❌ Использование: /settings auto_delete <дни>\n\n"
                    "Пример: /settings auto_delete 7"
                )
                return
            
            try:
                days = int(args[2])
                if days < 0:
                    await message.answer("❌ Количество дней не может быть отрицательным")
                    return
                if days > 365:
                    await message.answer("❌ Максимальное значение: 365 дней")
                    return
                
                await self.db.set_user_setting(
                    message.from_user.id, "auto_delete_days", days
                )
                
                if days == 0:
                    await message.answer("✅ Автоудаление выполненных задач отключено")
                else:
                    await message.answer(
                        f"✅ Автоудаление выполненных задач установлено: через {days} дн."
                    )
            except ValueError:
                await message.answer("❌ Количество дней должно быть числом")
        else:
            await message.answer("❌ Неизвестная настройка. Доступно: auto_delete")
    
    # ========== Callback обработчики для inline кнопок ==========
    
    async def callback_main_menu(self, callback: CallbackQuery) -> None:
        """Обработчик кнопки 'Главное меню'."""
        welcome_text = """
👋 Главное меню

Используйте кнопки для управления задачами!
"""
        try:
            await callback.message.edit_text(welcome_text, reply_markup=get_main_menu())
        except TelegramBadRequest as e:
            # Игнорируем ошибку, если сообщение не изменилось
            if "message is not modified" not in str(e).lower():
                raise
        await callback.answer()
    
    async def callback_list_tasks(self, callback: CallbackQuery) -> None:
        """Обработчик кнопки 'Мои задачи'."""
        await self._show_task_list(callback)
    
    async def callback_add_task(self, callback: CallbackQuery) -> None:
        """Обработчик кнопки 'Добавить задачу'."""
        text = (
            "➕ <b>Добавление задачи</b>\n\n"
            "📝 <b>Напишите текст задачи в чат</b>\n\n"
            "Вы можете указать время прямо в тексте:\n\n"
            "💡 <b>Примеры:</b>\n"
            "• Купить молоко в 14:30\n"
            "• Встреча в 2025-12-26 15:00\n"
            "• Оплатить счёт завтра 18:00\n"
            "• Позвонить маме (через 1 час)\n\n"
            "Или используйте команду: <code>/add ваш текст</code>"
        )
        
        # Создаем клавиатуру с кнопкой "Отмена" для возврата в меню
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="◀️ Отмена", callback_data="main_menu")
            ]]
        )
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except TelegramBadRequest as e:
            # Игнорируем ошибку, если сообщение не изменилось
            if "message is not modified" not in str(e).lower():
                raise
        await callback.answer("💡 Теперь напишите задачу в чат")
    
    async def callback_settings(self, callback: CallbackQuery) -> None:
        """Обработчик кнопки 'Настройки'."""
        auto_delete_days = await self.db.get_user_setting(
            callback.from_user.id, "auto_delete_days", 1
        )
        text = (
            f"⚙️ Настройки\n\n"
            f"🗑️ Автоудаление выполненных задач: через {auto_delete_days} дн."
            f"{' (по умолчанию)' if auto_delete_days == 1 else ''}\n\n"
            f"Выберите количество дней:"
        )
        keyboard = get_settings_keyboard(auto_delete_days)
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest as e:
            # Игнорируем ошибку, если сообщение не изменилось
            if "message is not modified" not in str(e).lower():
                raise
        await callback.answer()
    
    async def callback_task_done(self, callback: CallbackQuery) -> None:
        """Обработчик кнопки 'Выполнить задачу'."""
        task_id = int(callback.data.split("_")[-1])
        user_id = callback.from_user.id
        
        success = await self.task_service.mark_task_done(task_id, user_id)
        
        if success:
            await callback.answer("✅ Задача отмечена как выполненная!", show_alert=False)
            # Обновляем список задач
            await self._show_task_list(callback)
        else:
            await callback.answer("❌ Задача не найдена или уже выполнена", show_alert=True)
    
    async def callback_task_delete(self, callback: CallbackQuery) -> None:
        """Обработчик кнопки 'Удалить задачу'."""
        task_id = int(callback.data.split("_")[-1])
        user_id = callback.from_user.id
        
        success = await self.task_service.delete_task(task_id, user_id)
        
        if success:
            await callback.answer("🗑️ Задача удалена!", show_alert=False)
            # Обновляем список задач
            await self._show_task_list(callback)
        else:
            await callback.answer("❌ Задача не найдена", show_alert=True)
    
    async def callback_task_info(self, callback: CallbackQuery) -> None:
        """Обработчик для просмотра информации о выполненной задаче."""
        task_id = int(callback.data.split("_")[-1])
        tasks = await self.task_service.get_user_tasks(callback.from_user.id)
        task = next((t for t in tasks if t["id"] == task_id), None)
        
        if task:
            text = f"📋 Задача #{task_id}\n\n"
            text += f"📝 {task['text']}\n"
            text += f"📊 Статус: {'✅ Выполнена' if task['status'] == 'done' else '⏳ Активна'}\n"
            
            try:
                task_dt = datetime.fromisoformat(task["datetime"])
                dt_str = task_dt.strftime("%d.%m.%Y в %H:%M")
                text += f"⏰ Напоминание: {dt_str}\n"
            except:
                pass
            
            if task.get("completed_at"):
                try:
                    completed_dt = datetime.fromisoformat(task["completed_at"])
                    completed_str = completed_dt.strftime("%d.%m.%Y в %H:%M")
                    text += f"✅ Выполнена: {completed_str}"
                except:
                    pass
            
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(text="◀️ Назад к списку", callback_data="list_tasks")
                ]]
            )
            try:
                await callback.message.edit_text(text, reply_markup=keyboard)
            except TelegramBadRequest as e:
                # Игнорируем ошибку, если сообщение не изменилось
                if "message is not modified" not in str(e).lower():
                    raise
        else:
            await callback.answer("❌ Задача не найдена", show_alert=True)
        
        await callback.answer()
    
    async def callback_settings_auto_delete(self, callback: CallbackQuery) -> None:
        """Показывает текущие настройки автоудаления (открывает то же меню)."""
        await self.callback_settings(callback)
    
    async def callback_set_delete_days(self, callback: CallbackQuery) -> None:
        """Обработчик установки количества дней до автоудаления."""
        days_str = callback.data.split("_")[-1]
        
        try:
            days = int(days_str)
            if days < 0 or days > 365:
                await callback.answer("❌ Некорректное значение", show_alert=True)
                return
            
            await self.db.set_user_setting(callback.from_user.id, "auto_delete_days", days)
            
            if days == 0:
                await callback.answer("✅ Автоудаление отключено", show_alert=False)
            else:
                await callback.answer(f"✅ Установлено: {days} дн.", show_alert=False)
            
            # Обновляем меню настроек
            await self.callback_settings(callback)
        except ValueError:
            await callback.answer("❌ Ошибка при установке настройки", show_alert=True)
