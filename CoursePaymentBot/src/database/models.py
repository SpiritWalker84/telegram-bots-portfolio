"""Database models and CRUD operations."""
import aiosqlite
from datetime import datetime
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class Database:
    """Database class for user management using OOP."""

    def __init__(self, db_path: str):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

    async def create_table(self) -> None:
        """Create users table if not exists."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        paid BOOLEAN DEFAULT FALSE,
                        join_date TEXT,
                        payment_date TEXT
                    )
                    """
                )
                await db.commit()
                logger.info("Database table created/verified")
        except Exception as e:
            logger.error(f"Error creating database table: {e}")
            raise

    async def add_user(self, user_id: int) -> None:
        """
        Add new user to database.
        
        Args:
            user_id: Telegram user ID
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT OR IGNORE INTO users (user_id, join_date) VALUES (?, ?)",
                    (user_id, datetime.now().isoformat()),
                )
                await db.commit()
                logger.info(f"User {user_id} added to database")
        except Exception as e:
            logger.error(f"Error adding user {user_id}: {e}")
            raise

    async def set_paid(self, user_id: int, paid: bool = True) -> None:
        """
        Set user paid status.
        
        Args:
            user_id: Telegram user ID
            paid: Payment status (True/False)
        """
        try:
            payment_date = datetime.now().isoformat() if paid else None
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE users SET paid = ?, payment_date = ? WHERE user_id = ?",
                    (paid, payment_date, user_id),
                )
                await db.commit()
                logger.info(f"User {user_id} paid status set to {paid}")
        except Exception as e:
            logger.error(f"Error setting paid status for user {user_id}: {e}")
            raise

    async def is_paid(self, user_id: int) -> bool:
        """
        Check if user has paid.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if user has paid, False otherwise
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT paid FROM users WHERE user_id = ?", (user_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        return bool(row[0])
                    return False
        except Exception as e:
            logger.error(f"Error checking paid status for user {user_id}: {e}")
            return False

    async def get_user(self, user_id: int) -> Optional[dict]:
        """
        Get user information.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Dictionary with user data or None if not found
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT user_id, paid, join_date, payment_date FROM users WHERE user_id = ?",
                    (user_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        return {
                            "user_id": row[0],
                            "paid": bool(row[1]),
                            "join_date": row[2],
                            "payment_date": row[3]
                        }
                    return None
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
