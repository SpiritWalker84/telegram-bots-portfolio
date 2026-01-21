"""
CRUD операции с базой данных
"""
import aiosqlite
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    @asynccontextmanager
    async def get_connection(self):
        """Асинхронный контекст-менеджер для подключения к БД"""
        conn = await aiosqlite.connect(self.db_path)
        try:
            yield conn
            await conn.commit()
        except Exception as e:
            await conn.rollback()
            logger.error(f"Ошибка БД: {e}")
            raise
        finally:
            await conn.close()
    
    async def init_db(self):
        """Инициализация базы данных и создание таблиц"""
        async with self.get_connection() as conn:
            # Таблица услуг
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS services (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    duration INTEGER NOT NULL,  -- длительность в минутах
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
            
            # Таблица настроек
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
                    date TEXT NOT NULL,  -- YYYY-MM-DD
                    time TEXT NOT NULL,  -- HH:MM
                    status TEXT NOT NULL DEFAULT 'pending',  -- pending/confirmed/cancelled
                    notes TEXT,
                    reminder_sent INTEGER DEFAULT 0,  -- 0 = не отправлено, 1 = отправлено
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (service_id) REFERENCES services(id)
                )
            """)
            
            # Добавляем колонку reminder_sent, если её нет (для существующих БД)
            try:
                await conn.execute("ALTER TABLE appointments ADD COLUMN reminder_sent INTEGER DEFAULT 0")
            except aiosqlite.OperationalError:
                pass  # Колонка уже существует
            
            # Создание индексов для оптимизации
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
            logger.info("База данных инициализирована")
    
    # ========== CRUD для услуг ==========
    
    async def add_service(self, name: str, duration: int, price: Optional[float] = None, 
                         description: Optional[str] = None) -> int:
        """Добавить услугу"""
        async with self.get_connection() as conn:
            cursor = await conn.execute("""
                INSERT INTO services (name, duration, price, description)
                VALUES (?, ?, ?, ?)
            """, (name, duration, price, description))
            await conn.commit()
            return cursor.lastrowid
    
    async def get_service(self, service_id: int) -> Optional[Dict[str, Any]]:
        """Получить услугу по ID"""
        async with self.get_connection() as conn:
            async with conn.execute("""
                SELECT id, name, duration, price, description, is_active
                FROM services WHERE id = ?
            """, (service_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "name": row[1],
                        "duration": row[2],
                        "price": row[3],
                        "description": row[4],
                        "is_active": bool(row[5])
                    }
                return None
    
    async def get_all_services(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Получить все услуги"""
        async with self.get_connection() as conn:
            query = "SELECT id, name, duration, price, description, is_active FROM services"
            if active_only:
                query += " WHERE is_active = 1"
            query += " ORDER BY name"
            
            async with conn.execute(query) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "id": row[0],
                        "name": row[1],
                        "duration": row[2],
                        "price": row[3],
                        "description": row[4],
                        "is_active": bool(row[5]) if len(row) > 5 else True
                    }
                    for row in rows
                ]
    
    async def update_service(self, service_id: int, **kwargs) -> bool:
        """Обновить услугу"""
        allowed_fields = ["name", "duration", "price", "description", "is_active"]
        updates = []
        values = []
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                updates.append(f"{field} = ?")
                values.append(value)
        
        if not updates:
            return False
        
        values.append(service_id)
        query = f"UPDATE services SET {', '.join(updates)} WHERE id = ?"
        
        async with self.get_connection() as conn:
            cursor = await conn.execute(query, values)
            await conn.commit()
            return cursor.rowcount > 0
    
    async def delete_service(self, service_id: int) -> bool:
        """Удалить услугу (мягкое удаление)"""
        return await self.update_service(service_id, is_active=0)
    
    # ========== CRUD для записей ==========
    
    async def add_appointment(self, client_id: int, client_name: str, 
                             service_id: int, date: str, time: str,
                             client_username: Optional[str] = None,
                             notes: Optional[str] = None) -> int:
        """Добавить запись"""
        async with self.get_connection() as conn:
            cursor = await conn.execute("""
                INSERT INTO appointments 
                (client_id, client_name, client_username, service_id, date, time, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (client_id, client_name, client_username, service_id, date, time, notes))
            await conn.commit()
            return cursor.lastrowid
    
    async def get_appointment(self, appointment_id: int) -> Optional[Dict[str, Any]]:
        """Получить запись по ID"""
        async with self.get_connection() as conn:
            async with conn.execute("""
                SELECT a.id, a.client_id, a.client_name, a.client_username,
                       a.service_id, s.name as service_name, a.date, a.time,
                       a.status, a.notes, a.created_at
                FROM appointments a
                LEFT JOIN services s ON a.service_id = s.id
                WHERE a.id = ?
            """, (appointment_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "client_id": row[1],
                        "client_name": row[2],
                        "client_username": row[3],
                        "service_id": row[4],
                        "service_name": row[5],
                        "date": row[6],
                        "time": row[7],
                        "status": row[8],
                        "notes": row[9],
                        "created_at": row[10]
                    }
                return None
    
    async def get_appointments_by_date(self, date: str) -> List[Dict[str, Any]]:
        """Получить все записи на дату"""
        async with self.get_connection() as conn:
            async with conn.execute("""
                SELECT a.id, a.client_id, a.client_name, a.client_username,
                       a.service_id, s.name as service_name, a.date, a.time,
                       a.status, a.notes
                FROM appointments a
                LEFT JOIN services s ON a.service_id = s.id
                WHERE a.date = ? AND a.status != 'cancelled'
                ORDER BY a.time
            """, (date,)) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "id": row[0],
                        "client_id": row[1],
                        "client_name": row[2],
                        "client_username": row[3],
                        "service_id": row[4],
                        "service_name": row[5],
                        "date": row[6],
                        "time": row[7],
                        "status": row[8],
                        "notes": row[9]
                    }
                    for row in rows
                ]
    
    async def get_appointments_by_client(self, client_id: int, 
                                        limit: int = 10) -> List[Dict[str, Any]]:
        """Получить записи клиента"""
        async with self.get_connection() as conn:
            async with conn.execute("""
                SELECT a.id, a.client_id, a.client_name, a.service_id,
                       s.name as service_name, a.date, a.time, a.status, a.notes
                FROM appointments a
                LEFT JOIN services s ON a.service_id = s.id
                WHERE a.client_id = ?
                ORDER BY a.date DESC, a.time DESC
                LIMIT ?
            """, (client_id, limit)) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "id": row[0],
                        "client_id": row[1],
                        "client_name": row[2],
                        "service_id": row[3],
                        "service_name": row[4],
                        "date": row[5],
                        "time": row[6],
                        "status": row[7],
                        "notes": row[8]
                    }
                    for row in rows
                ]
    
    async def get_available_times(self, date: str, service_id: int, config) -> List[str]:
        """Получить доступные времена для записи"""
        # Получаем время работы из настроек или используем значения по умолчанию
        WORKING_HOURS_START, WORKING_HOURS_END = await self.get_working_hours(config)
        APPOINTMENT_INTERVAL = config.APPOINTMENT_INTERVAL
        
        # Получаем длительность услуги
        service = await self.get_service(service_id)
        if not service:
            return []
        
        duration = service["duration"]
        
        # Проверяем, является ли дата сегодняшней
        today = datetime.now().date()
        selected_date = datetime.strptime(date, "%Y-%m-%d").date()
        is_today = selected_date == today
        
        # Получаем текущее время, если дата сегодняшняя
        current_time = None
        if is_today:
            now = datetime.now()
            current_time = (now.hour, now.minute)
        
        # Получаем занятые времена
        async with self.get_connection() as conn:
            async with conn.execute("""
                SELECT time FROM appointments
                WHERE date = ? AND status != 'cancelled'
                ORDER BY time
            """, (date,)) as cursor:
                busy_times = {row[0] for row in await cursor.fetchall()}
        
        # Генерируем доступные времена
        available = []
        current_hour = WORKING_HOURS_START
        current_minute = 0
        
        while current_hour < WORKING_HOURS_END or (current_hour == WORKING_HOURS_END and current_minute == 0):
            time_str = f"{current_hour:02d}:{current_minute:02d}"
            
            # Если дата сегодняшняя, проверяем, не прошло ли время
            if is_today and current_time:
                if (current_hour < current_time[0]) or (current_hour == current_time[0] and current_minute <= current_time[1]):
                    # Время уже прошло, пропускаем
                    current_minute += APPOINTMENT_INTERVAL
                    if current_minute >= 60:
                        current_hour += current_minute // 60
                        current_minute = current_minute % 60
                    continue
            
            # Проверяем, не пересекается ли с занятыми временами
            is_busy = False
            for busy_time in busy_times:
                busy_h, busy_m = map(int, busy_time.split(":"))
                # Проверяем пересечение интервалов
                end_h = current_hour + (current_minute + duration) // 60
                end_m = (current_minute + duration) % 60
                busy_end_h = busy_h + (busy_m + duration) // 60
                busy_end_m = (busy_m + duration) % 60
                
                if not (end_h < busy_h or (end_h == busy_h and end_m <= busy_m) or
                       current_hour > busy_end_h or (current_hour == busy_end_h and current_minute >= busy_end_m)):
                    is_busy = True
                    break
            
            if not is_busy:
                available.append(time_str)
            
            # Переходим к следующему слоту
            current_minute += APPOINTMENT_INTERVAL
            if current_minute >= 60:
                current_hour += current_minute // 60
                current_minute = current_minute % 60
        
        return available
    
    async def get_all_times_with_availability(self, date: str, service_id: int, config) -> List[dict]:
        """Получить все времена с информацией о доступности"""
        # Получаем время работы из настроек или используем значения по умолчанию
        WORKING_HOURS_START, WORKING_HOURS_END = await self.get_working_hours(config)
        
        # Получаем интервал из настроек
        interval = int(await self.get_setting("appointment_interval", str(config.APPOINTMENT_INTERVAL)))
        
        # Получаем длительность услуги
        service = await self.get_service(service_id)
        if not service:
            return []
        
        duration = service["duration"]
        
        # Проверяем, является ли дата сегодняшней
        today = datetime.now().date()
        selected_date = datetime.strptime(date, "%Y-%m-%d").date()
        is_today = selected_date == today
        
        # Получаем текущее время, если дата сегодняшняя
        current_time = None
        if is_today:
            now = datetime.now()
            current_time = (now.hour, now.minute)
        
        # Получаем занятые времена
        async with self.get_connection() as conn:
            async with conn.execute("""
                SELECT time FROM appointments
                WHERE date = ? AND status != 'cancelled'
                ORDER BY time
            """, (date,)) as cursor:
                busy_times = {row[0] for row in await cursor.fetchall()}
        
        # Генерируем все времена с информацией о доступности
        all_times = []
        current_hour = WORKING_HOURS_START
        current_minute = 0
        
        while current_hour < WORKING_HOURS_END or (current_hour == WORKING_HOURS_END and current_minute == 0):
            time_str = f"{current_hour:02d}:{current_minute:02d}"
            
            # Если дата сегодняшняя, проверяем, не прошло ли время
            is_past = False
            if is_today and current_time:
                if (current_hour < current_time[0]) or (current_hour == current_time[0] and current_minute <= current_time[1]):
                    is_past = True
            
            # Проверяем, не пересекается ли с занятыми временами
            is_busy = False
            if not is_past:
                for busy_time in busy_times:
                    busy_h, busy_m = map(int, busy_time.split(":"))
                    # Получаем длительность занятой услуги
                    busy_service = await self.get_service_by_appointment_time(date, busy_time)
                    busy_duration = duration  # Используем длительность текущей услуги для проверки
                    if busy_service:
                        busy_duration = busy_service.get("duration", duration)
                    
                    # Проверяем пересечение интервалов
                    end_h = current_hour + (current_minute + duration) // 60
                    end_m = (current_minute + duration) % 60
                    busy_end_h = busy_h + (busy_m + busy_duration) // 60
                    busy_end_m = (busy_m + busy_duration) % 60
                    
                    if not (end_h < busy_h or (end_h == busy_h and end_m <= busy_m) or
                           current_hour > busy_end_h or (current_hour == busy_end_h and current_minute >= busy_end_m)):
                        is_busy = True
                        break
            
            all_times.append({
                "time": time_str,
                "available": not is_busy and not is_past,
                "is_past": is_past
            })
            
            # Переходим к следующему слоту
            current_minute += interval
            if current_minute >= 60:
                current_hour += current_minute // 60
                current_minute = current_minute % 60
        
        return all_times
    
    async def get_service_by_appointment_time(self, date: str, time: str) -> Optional[dict]:
        """Получить услугу по времени записи"""
        async with self.get_connection() as conn:
            async with conn.execute("""
                SELECT s.id, s.name, s.duration, s.price, s.description, s.is_active
                FROM appointments a
                JOIN services s ON a.service_id = s.id
                WHERE a.date = ? AND a.time = ? AND a.status != 'cancelled'
                LIMIT 1
            """, (date, time)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "name": row[1],
                        "duration": row[2],
                        "price": row[3],
                        "description": row[4],
                        "is_active": bool(row[5])
                    }
        return None
    
    async def update_appointment_status(self, appointment_id: int, 
                                       status: str) -> bool:
        """Обновить статус записи"""
        async with self.get_connection() as conn:
            cursor = await conn.execute("""
                UPDATE appointments 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, appointment_id))
            await conn.commit()
            return cursor.rowcount > 0
    
    async def cancel_appointment(self, appointment_id: int) -> bool:
        """Отменить запись"""
        return await self.update_appointment_status(appointment_id, "cancelled")
    
    async def confirm_appointment(self, appointment_id: int) -> bool:
        """Подтвердить запись"""
        return await self.update_appointment_status(appointment_id, "confirmed")
    
    async def get_appointments_for_reminder(self, minutes_before: int = 30) -> List[Dict[str, Any]]:
        """Получить записи, для которых нужно отправить напоминание"""
        now = datetime.now()
        reminder_time = now + timedelta(minutes=minutes_before)
        
        target_date = reminder_time.strftime("%Y-%m-%d")
        target_time = reminder_time.strftime("%H:%M")
        
        async with self.get_connection() as conn:
            async with conn.execute("""
                SELECT a.id, a.client_id, a.client_name, a.client_username,
                       a.service_id, s.name as service_name, a.date, a.time,
                       a.status, a.notes
                FROM appointments a
                LEFT JOIN services s ON a.service_id = s.id
                WHERE a.date = ? 
                  AND a.time = ?
                  AND a.status = 'confirmed'
                  AND a.reminder_sent = 0
            """, (target_date, target_time)) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "id": row[0],
                        "client_id": row[1],
                        "client_name": row[2],
                        "client_username": row[3],
                        "service_id": row[4],
                        "service_name": row[5],
                        "date": row[6],
                        "time": row[7],
                        "status": row[8],
                        "notes": row[9]
                    }
                    for row in rows
                ]
    
    async def mark_reminder_sent(self, appointment_id: int) -> bool:
        """Отметить, что напоминание отправлено"""
        async with self.get_connection() as conn:
            cursor = await conn.execute("""
                UPDATE appointments 
                SET reminder_sent = 1
                WHERE id = ?
            """, (appointment_id,))
            await conn.commit()
            return cursor.rowcount > 0
    
    # ========== CRUD для администраторов ==========
    
    async def add_admin(self, user_id: int, username: Optional[str] = None,
                       full_name: Optional[str] = None) -> bool:
        """Добавить администратора"""
        async with self.get_connection() as conn:
            try:
                await conn.execute("""
                    INSERT INTO admins (user_id, username, full_name)
                    VALUES (?, ?, ?)
                """, (user_id, username, full_name))
                await conn.commit()
                return True
            except aiosqlite.IntegrityError:
                return False
    
    async def is_admin(self, user_id: int) -> bool:
        """Проверить, является ли пользователь администратором"""
        async with self.get_connection() as conn:
            async with conn.execute("""
                SELECT 1 FROM admins WHERE user_id = ?
            """, (user_id,)) as cursor:
                return (await cursor.fetchone()) is not None
    
    async def get_all_admins(self) -> List[Dict[str, Any]]:
        """Получить всех администраторов"""
        async with self.get_connection() as conn:
            async with conn.execute("""
                SELECT user_id, username, full_name FROM admins
            """) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "user_id": row[0],
                        "username": row[1],
                        "full_name": row[2]
                    }
                    for row in rows
                ]
    
    # ========== CRUD для настроек ==========
    
    async def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Получить настройку"""
        async with self.get_connection() as conn:
            async with conn.execute("""
                SELECT value FROM settings WHERE key = ?
            """, (key,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else default
    
    async def set_setting(self, key: str, value: str) -> bool:
        """Установить настройку"""
        async with self.get_connection() as conn:
            try:
                await conn.execute("""
                    INSERT OR REPLACE INTO settings (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (key, value))
                await conn.commit()
                return True
            except Exception as e:
                logger.error(f"Ошибка при сохранении настройки: {e}")
                return False
    
    async def get_working_hours(self, config) -> tuple[int, int]:
        """Получить время работы (начало, конец)"""
        start = await self.get_setting("working_hours_start", str(config.WORKING_HOURS_START))
        end = await self.get_setting("working_hours_end", str(config.WORKING_HOURS_END))
        return (int(start), int(end))
