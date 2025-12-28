"""
Миграция: начальная схема базы данных
"""
import aiosqlite
import logging

logger = logging.getLogger(__name__)


async def up(db_path: str):
    """Применение миграции"""
    async with aiosqlite.connect(db_path) as conn:
        # Таблица услуг
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                duration INTEGER NOT NULL,
                price REAL,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица администраторов
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY,
                user_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица записей
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                client_name TEXT,
                client_username TEXT,
                service_id INTEGER,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (service_id) REFERENCES services(id)
            )
        """)
        
        # Индексы
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_date_time 
            ON appointments(date, time)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_status 
            ON appointments(status)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_client_id 
            ON appointments(client_id)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_service_id 
            ON appointments(service_id)
        """)
        
        await conn.commit()
        logger.info("Миграция 001 применена: начальная схема создана")


async def down(db_path: str):
    """Откат миграции"""
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute("DROP INDEX IF EXISTS idx_service_id")
        await conn.execute("DROP INDEX IF EXISTS idx_client_id")
        await conn.execute("DROP INDEX IF EXISTS idx_status")
        await conn.execute("DROP INDEX IF EXISTS idx_date_time")
        await conn.execute("DROP TABLE IF EXISTS appointments")
        await conn.execute("DROP TABLE IF EXISTS admins")
        await conn.execute("DROP TABLE IF EXISTS services")
        await conn.commit()
        logger.info("Миграция 001 откачена")




