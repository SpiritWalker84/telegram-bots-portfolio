"""Admin notifications service."""

import asyncio
import logging
from typing import Callable, Optional

from aiogram import Bot


logger = logging.getLogger(__name__)


async def notify_admins_about_new_appointment(
    *,
    bot: Bot,
    db,
    appointment_id: int,
    admin_id: int,
    status_ru: Callable[[str], str],
    delete_after_seconds: int = 5,
) -> None:
    """Notify all admins about new appointment and auto-delete messages."""
    appointment = await db.get_appointment(appointment_id)
    if not appointment:
        return

    admins = await db.get_all_admins()
    if admin_id not in [a["user_id"] for a in admins]:
        admins.append({"user_id": admin_id})

    text = "🔔 **Новая запись**\n\n"
    text += f"Номер: #{appointment_id}\n"
    text += f"Клиент: {appointment['client_name']}\n"
    if appointment.get("client_username"):
        text += f"Username: @{appointment['client_username']}\n"
    text += f"Услуга: {appointment['service_name']}\n"
    text += f"Дата: {appointment['date']}\n"
    text += f"Время: {appointment['time']}\n"
    text += f"Статус: {status_ru(appointment['status'])}"

    sent_messages = []
    for admin in admins:
        try:
            msg = await bot.send_message(admin["user_id"], text, parse_mode="Markdown")
            sent_messages.append(msg)
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление админу {admin['user_id']}: {e}")

    async def delete_messages_after_delay() -> None:
        await asyncio.sleep(delete_after_seconds)
        for msg in sent_messages:
            try:
                await msg.delete()
            except Exception as e:
                logger.error(f"Не удалось удалить уведомление: {e}")

    asyncio.create_task(delete_messages_after_delay())

