"""Appointment reminder background job."""

import asyncio
import logging
from typing import Any, Dict

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.utils.retry import retry_send_message

logger = logging.getLogger(__name__)


def _reminder_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Мои записи", callback_data="my_appointments")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
        ]
    )


async def send_appointment_reminder(*, bot: Bot, db, appointment: Dict[str, Any]) -> bool:
    """Send reminder to client and mark reminder_sent."""
    text = "🔔 **Напоминание о записи**\n\n"
    text += "Через 30 минут у вас запись:\n\n"
    text += f"📋 Услуга: {appointment['service_name']}\n"
    text += f"📅 Дата: {appointment['date']}\n"
    text += f"⏰ Время: {appointment['time']}\n\n"
    text += "Не забудьте прийти вовремя!"

    # Используем retry-логику для отправки сообщения
    result = await retry_send_message(
        func=lambda: bot.send_message(
            appointment["client_id"],
            text,
            reply_markup=_reminder_keyboard(),
            parse_mode="Markdown",
        ),
        max_attempts=3,
        delay=2.0,
        error_message=f"Ошибка при отправке напоминания клиенту {appointment.get('client_id')}"
    )

    if result is not None:
        await db.mark_reminder_sent(appointment["id"])
        logger.info(
            f"Напоминание отправлено клиенту {appointment['client_id']} для записи #{appointment['id']}"
        )
        return True
    
    return False


async def check_and_send_reminders(*, bot: Bot, db, minutes_before: int = 30) -> None:
    """Loop: check DB and send reminders periodically."""
    try:
        while True:
            try:
                appointments = await db.get_appointments_for_reminder(minutes_before=minutes_before)

                for appointment in appointments:
                    # Проверяем отмену перед каждой итерацией
                    await asyncio.sleep(0)  # Даем возможность отменить задачу
                    await send_appointment_reminder(bot=bot, db=db, appointment=appointment)
                    await asyncio.sleep(0.5)

                # Проверяем отмену перед длительным sleep
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                logger.info("Задача проверки напоминаний отменена")
                raise  # Пробрасываем CancelledError дальше
            except Exception as e:
                logger.error(f"Ошибка в задаче проверки напоминаний: {e}", exc_info=True)
                # Проверяем отмену перед повторной попыткой
                try:
                    await asyncio.sleep(60)
                except asyncio.CancelledError:
                    logger.info("Задача проверки напоминаний отменена во время ожидания")
                    raise
    except asyncio.CancelledError:
        logger.info("Задача проверки напоминаний завершена")
        raise

