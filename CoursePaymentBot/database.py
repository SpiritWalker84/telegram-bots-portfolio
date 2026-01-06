"""SQLite database CRUD operations."""
import aiosqlite
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Database:
    """Database CRUD class for user management."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    async def create_table(self) -> None:
        """Create users table if not exists."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    paid BOOLEAN DEFAULT FALSE,
                    join_date TEXT
                )
                """
            )
            await db.commit()
            logger.info("Database table created/verified")

    async def add_user(self, user_id: int) -> None:
        """Add new user to database."""
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

    async def set_paid(self, user_id: int, paid: bool = True) -> None:
        """Set user paid status."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE users SET paid = ? WHERE user_id = ?",
                    (paid, user_id),
                )
                await db.commit()
                logger.info(f"User {user_id} paid status set to {paid}")
        except Exception as e:
            logger.error(f"Error setting paid status for user {user_id}: {e}")

    async def is_paid(self, user_id: int) -> bool:
        """Check if user has paid."""
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

