"""Payment processing service using OOP."""
from aiogram import Bot
from aiogram.types import LabeledPrice, PreCheckoutQuery
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class PaymentService:
    """Service for handling payment operations."""

    def __init__(self, provider_token: str, course_price: int):
        """
        Initialize payment service.
        
        Args:
            provider_token: Telegram Payments provider token
            course_price: Course price in rubles
        """
        self.provider_token = provider_token
        self.course_price = course_price

    async def send_invoice(
        self, bot: Bot, user_id: int
    ) -> None:
        """
        Send invoice for course purchase.
        
        Args:
            bot: Telegram bot instance
            user_id: Telegram user ID
        """
        try:
            logger.info(f"Attempting to send invoice to user {user_id}")
            
            if not self.provider_token or len(self.provider_token) < 10:
                raise ValueError("Provider token is empty or invalid")
            
            await bot.send_invoice(
                chat_id=user_id,
                title="Онлайн-курс",
                description="Полный доступ к онлайн-курсу",
                payload="course_payment",
                provider_token=self.provider_token,
                currency="RUB",
                prices=[LabeledPrice(label="Курс", amount=self.course_price * 100)],
                start_parameter="course",
            )
            logger.info(f"Invoice sent to user {user_id}")
        except Exception as e:
            logger.error(f"Error sending invoice to user {user_id}: {e}")
            raise

    async def process_pre_checkout(
        self, pre_checkout_query: PreCheckoutQuery, bot: Bot
    ) -> None:
        """
        Process pre-checkout query.
        
        Args:
            pre_checkout_query: Pre-checkout query from Telegram
            bot: Telegram bot instance
        """
        try:
            await bot.answer_pre_checkout_query(
                pre_checkout_query_id=pre_checkout_query.id, ok=True
            )
            logger.info(f"Pre-checkout approved for user {pre_checkout_query.from_user.id}")
        except Exception as e:
            logger.error(f"Error processing pre-checkout: {e}")
            raise

    async def create_invite_link(
        self, bot: Bot, channel_id: str, user_id: int
    ) -> Optional[str]:
        """
        Create invite link for paid user.
        
        Args:
            bot: Telegram bot instance
            channel_id: Channel ID
            user_id: Telegram user ID
            
        Returns:
            Invite link or None if failed
        """
        try:
            # Unban user in channel (if previously banned)
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
                return link
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error creating invite link for channel {channel_id}: {e}")
                if "chat not found" in error_msg.lower() or "chat_id" in error_msg.lower():
                    logger.error(
                        f"Channel {channel_id} not found or bot is not admin. "
                        f"Please check CHANNEL_ID in .env"
                    )
                return None
        except Exception as e:
            logger.error(f"Error creating invite link for user {user_id}: {e}")
            return None
