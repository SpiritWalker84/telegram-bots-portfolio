"""Payment processing functions."""
from aiogram import Bot
from aiogram.types import LabeledPrice, PreCheckoutQuery, SuccessfulPayment
from typing import Optional
import logging

logger = logging.getLogger(__name__)


async def send_course_invoice(
    bot: Bot, user_id: int, provider_token: str, price: int
) -> None:
    """Send invoice for course purchase."""
    try:
        logger.info(f"Attempting to send invoice to user {user_id}")
        logger.info(f"Provider token (full): {provider_token}")
        logger.info(f"Provider token length: {len(provider_token)}")
        
        await bot.send_invoice(
            chat_id=user_id,
            title="Онлайн-курс",
            description="Полный доступ к онлайн-курсу",
            payload="course_payment",
            provider_token=provider_token,
            currency="RUB",
            prices=[LabeledPrice(label="Курс", amount=price * 100)],
            start_parameter="course",
        )
        logger.info(f"Invoice sent to user {user_id}")
    except Exception as e:
        logger.error(f"Error sending invoice to user {user_id}: {e}")
        logger.error(f"Provider token (full): {provider_token}")
        logger.error(f"Provider token length: {len(provider_token)}")
        raise


async def process_pre_checkout_query(
    pre_checkout_query: PreCheckoutQuery, bot: Bot
) -> None:
    """Process pre-checkout query."""
    try:
        await bot.answer_pre_checkout_query(
            pre_checkout_query_id=pre_checkout_query.id, ok=True
        )
        logger.info(f"Pre-checkout approved for user {pre_checkout_query.from_user.id}")
    except Exception as e:
        logger.error(f"Error processing pre-checkout: {e}")
        raise


async def process_successful_payment(
    bot: Bot,
    user_id: int,
    channel_id: str,
    db,
) -> Optional[str]:
    """Process successful payment: unban user, create invite link, update DB."""
    try:
        # Unban user in channel
        try:
            await bot.unban_chat_member(chat_id=channel_id, user_id=user_id)
            logger.info(f"User {user_id} unbanned in channel {channel_id}")
        except Exception as e:
            logger.warning(f"Could not unban user {user_id}: {e}")

        # Create invite link
        try:
            invite_link = await bot.create_chat_invite_link(
                chat_id=channel_id, member_limit=1
            )
            link = invite_link.invite_link
            logger.info(f"Invite link created for user {user_id}: {link}")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error creating invite link for channel {channel_id}: {e}")
            if "chat not found" in error_msg.lower() or "chat_id" in error_msg.lower():
                logger.error(f"Channel {channel_id} not found or bot is not admin. Please check CHANNEL_ID in .env")
            link = None

        # Update database
        await db.set_paid(user_id, paid=True)

        return link
    except Exception as e:
        logger.error(f"Error processing successful payment for user {user_id}: {e}")
        return None

