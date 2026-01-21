"""Утилиты для парсинга времени из текста."""
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple


class TimeParser:
    """Класс для парсинга времени из текста задачи."""
    
    @staticmethod
    def parse_time_from_text(text: str) -> Tuple[Optional[datetime], str]:
        """
        Парсит время из текста задачи и возвращает кортеж (время, очищенный текст).
        
        Поддерживаемые форматы:
        - "в 2025-12-26 15:00" или "2025-12-26 15:00"
        - "завтра HH:MM" или "завтра в HH:MM"
        - "в HH:MM" или просто "HH:MM" (сегодня)
        
        Args:
            text: Текст задачи с временем
            
        Returns:
            Кортеж (reminder_time, cleaned_text), где reminder_time может быть None
        """
        now = datetime.now()
        reminder_time = None
        task_text = text
        
        # 1. Парсинг формата: "в 2025-12-26 15:00" или "2025-12-26 15:00"
        date_time_pattern = r'(?:в\s+)?(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{2})'
        match = re.search(date_time_pattern, text)
        
        if match:
            try:
                year = int(match.group(1))
                month = int(match.group(2))
                day = int(match.group(3))
                hours = int(match.group(4))
                minutes = int(match.group(5))
                
                if not (1 <= month <= 12 and 1 <= day <= 31 and 0 <= hours <= 23 and 0 <= minutes <= 59):
                    raise ValueError("Неверный формат даты/времени")
                
                reminder_time = datetime(year, month, day, hours, minutes, 0)
                
                # Удаляем дату и время из текста задачи
                task_text = re.sub(date_time_pattern, '', text, flags=re.IGNORECASE).strip()
                task_text = re.sub(r'\s+', ' ', task_text)
                
            except (ValueError, AttributeError):
                return None, text  # Возвращаем исходный текст при ошибке
        
        # 2. Парсинг формата: "завтра HH:MM" или "завтра в HH:MM"
        if not reminder_time:
            tomorrow_pattern = r'завтра\s+(?:в\s+)?(\d{1,2}):(\d{2})'
            match = re.search(tomorrow_pattern, text, re.IGNORECASE)
            
            if match:
                try:
                    hours = int(match.group(1))
                    minutes = int(match.group(2))
                    
                    if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
                        raise ValueError("Неверный формат времени")
                    
                    # Устанавливаем на завтра
                    reminder_time = (now + timedelta(days=1)).replace(
                        hour=hours, minute=minutes, second=0, microsecond=0
                    )
                    
                    # Удаляем "завтра" и время из текста задачи
                    task_text = re.sub(tomorrow_pattern, '', text, flags=re.IGNORECASE).strip()
                    task_text = re.sub(r'\s+', ' ', task_text)
                    
                except (ValueError, AttributeError):
                    pass
        
        # 3. Парсинг формата: "в HH:MM" или просто "HH:MM" (сегодня)
        if not reminder_time:
            time_pattern = r'в\s+(\d{1,2}):(\d{2})|^(\d{1,2}):(\d{2})$'
            match = re.search(time_pattern, text, re.IGNORECASE)
            
            if match:
                try:
                    hours = int(match.group(1) or match.group(3))
                    minutes = int(match.group(2) or match.group(4))
                    
                    if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
                        raise ValueError("Неверный формат времени")
                    
                    # Устанавливаем время на сегодня
                    reminder_time = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
                    
                    # Если время уже прошло сегодня, устанавливаем на завтра
                    if reminder_time <= now:
                        reminder_time += timedelta(days=1)
                    
                    # Удаляем время из текста задачи
                    task_text = re.sub(time_pattern, '', text, flags=re.IGNORECASE).strip()
                    task_text = re.sub(r'\s+', ' ', task_text)
                    
                except (ValueError, AttributeError):
                    pass
        
        # Очистка текста задачи
        if not task_text:
            task_text = "Задача без описания"
        
        return reminder_time, task_text
