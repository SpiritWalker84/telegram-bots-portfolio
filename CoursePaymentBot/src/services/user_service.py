"""User management service using OOP."""
from aiogram import Bot
from typing import Optional
import logging

from src.database.models import Database

logger = logging.getLogger(__name__)


class UserService:
    """Service for handling user operations."""

    def __init__(self, db: Database):
        """
        Initialize user service.
        
        Args:
            db: Database instance
        """
        self.db = db

    async def register_user(self, user_id: int) -> None:
        """
        Register new user in database.
        
        Args:
            user_id: Telegram user ID
        """
        try:
            await self.db.add_user(user_id)
            logger.info(f"User {user_id} registered")
        except Exception as e:
            logger.error(f"Error registering user {user_id}: {e}")
            raise

    async def check_payment_status(self, user_id: int) -> bool:
        """
        Check if user has paid.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if user has paid, False otherwise
        """
        return await self.db.is_paid(user_id)

    async def process_payment(
        self, user_id: int, bot: Bot, channel_id: str, payment_service
    ) -> Optional[str]:
        """
        Process successful payment: update database and create invite link.
        
        Args:
            user_id: Telegram user ID
            bot: Telegram bot instance
            channel_id: Channel ID
            payment_service: PaymentService instance
            
        Returns:
            Invite link or None if failed
        """
        try:
            # Update database
            await self.db.set_paid(user_id, paid=True)
            logger.info(f"Payment processed for user {user_id}")
            
            # Create invite link
            invite_link = await payment_service.create_invite_link(
                bot, channel_id, user_id
            )
            
            return invite_link
        except Exception as e:
            logger.error(f"Error processing payment for user {user_id}: {e}")
            return None

    async def get_user_info(self, user_id: int) -> Optional[dict]:
        """
        Get user information.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Dictionary with user data or None if not found
        """
        return await self.db.get_user(user_id)
