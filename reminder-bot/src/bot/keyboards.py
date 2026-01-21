"""Inline клавиатуры для бота."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any


def get_main_menu() -> InlineKeyboardMarkup:
    """Главное меню с основными действиями."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 Мои задачи", callback_data="list_tasks"),
                InlineKeyboardButton(text="➕ Добавить задачу", callback_data="add_task")
            ],
            [
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")
            ]
        ]
    )


def get_task_list_keyboard(
    pending_tasks: List[Dict[str, Any]],
    done_tasks: List[Dict[str, Any]]
) -> InlineKeyboardMarkup:
    """
    Клавиатура для списка задач с кнопками управления.
    
    Args:
        pending_tasks: Список активных задач
        done_tasks: Список выполненных задач
    """
    keyboard = []
    
    # Кнопки для активных задач
    if pending_tasks:
        for task in pending_tasks[:10]:  # Показываем максимум 10 задач
            task_id = task["id"]
            task_text = task["text"]
            # Обрезаем длинный текст
            if len(task_text) > 30:
                task_text = task_text[:27] + "..."
            
            keyboard.append([
                InlineKeyboardButton(
                    text=f"✅ #{task_id} {task_text}",
                    callback_data=f"task_done_{task_id}"
                ),
                InlineKeyboardButton(
                    text="🗑️",
                    callback_data=f"task_delete_{task_id}"
                )
            ])
    
    # Кнопки для выполненных задач (только последние 5)
    if done_tasks:
        for task in done_tasks[:5]:
            task_id = task["id"]
            task_text = task["text"]
            if len(task_text) > 25:
                task_text = task_text[:22] + "..."
            
            keyboard.append([
                InlineKeyboardButton(
                    text=f"❌ #{task_id} {task_text}",
                    callback_data=f"task_info_{task_id}"
                ),
                InlineKeyboardButton(
                    text="🗑️",
                    callback_data=f"task_delete_{task_id}"
                )
            ])
    
    # Кнопка обновления списка
    keyboard.append([
        InlineKeyboardButton(text="🔄 Обновить", callback_data="list_tasks"),
        InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_empty_tasks_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура когда нет задач."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Добавить задачу", callback_data="add_task"),
                InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")
            ]
        ]
    )


def get_settings_keyboard(auto_delete_days: int) -> InlineKeyboardMarkup:
    """
    Клавиатура настроек автоудаления.
    
    Args:
        auto_delete_days: Текущее количество дней до автоудаления
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="🗑️ Автоудаление: 1 день" if auto_delete_days == 1 else f"🗑️ Автоудаление: {auto_delete_days} дн.",
                callback_data="settings_auto_delete"
            )
        ],
        [
            InlineKeyboardButton(text="1 день", callback_data="set_delete_1"),
            InlineKeyboardButton(text="3 дня", callback_data="set_delete_3"),
            InlineKeyboardButton(text="7 дней", callback_data="set_delete_7")
        ],
        [
            InlineKeyboardButton(text="14 дней", callback_data="set_delete_14"),
            InlineKeyboardButton(text="30 дней", callback_data="set_delete_30"),
            InlineKeyboardButton(text="Отключить", callback_data="set_delete_0")
        ],
        [
            InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
