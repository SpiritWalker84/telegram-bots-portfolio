#!/usr/bin/env python3
"""
Простой тест для проверки логики просмотра карточек
Запуск: python test_views_simple.py
"""
import os
import sys
from datetime import datetime, timedelta

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 60)
print("Тест логики просмотра карточек товаров")
print("=" * 60)

# 1. Проверка конфигурации
print("\n1. Проверка конфигурации...")
try:
    from config import Config
    config = Config.from_env()
    analytics_key = config.wb_analytics_api_key or config.wb_api_key
    print(f"   ✓ WB_API_KEY: {config.wb_api_key[:10]}...")
    print(f"   ✓ Analytics API Key: {analytics_key[:10]}...")
    print(f"   ✓ Analytics client будет создан: {analytics_key is not None}")
except Exception as e:
    print(f"   ✗ Ошибка: {e}")
    sys.exit(1)

# 2. Проверка инициализации Analytics клиента
print("\n2. Инициализация Analytics API клиента...")
try:
    from api.analytics_client import WBAnalyticsClient
    analytics_client = WBAnalyticsClient(analytics_key)
    print("   ✓ Клиент создан успешно")
except Exception as e:
    print(f"   ✗ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 3. Тест запроса к API
print("\n3. Тест запроса к Analytics API...")
yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
print(f"   Дата запроса: {yesterday}")

try:
    # Включаем DEBUG логирование для детальной информации
    import logging
    logging.getLogger('api.analytics_client').setLevel(logging.DEBUG)
    logging.getLogger('api.content_client').setLevel(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG)
    
    # Пробуем также получить данные за сегодня (может быть доступнее)
    today = datetime.utcnow().strftime('%Y-%m-%d')
    print(f"\n   Также проверяем сегодняшнюю дату: {today}")
    
    print(f"\n   Получение списка товаров для запроса...")
    # Получаем список товаров через Content API
    nm_ids = None
    try:
        from api.content_client import WBContentClient
        content_client = WBContentClient(config.wb_api_key)
        cards = content_client.get_all_cards()
        nm_ids = [card.get("nmID") for card in cards if card.get("nmID")]
        print(f"   ✓ Получено {len(nm_ids)} nmIds")
        
        # Создаем маппинг nmId -> vendorCode
        nm_to_vendor = {card.get("nmID"): card.get("vendorCode", "").strip() 
                       for card in cards if card.get("nmID") and card.get("vendorCode")}
        print(f"   ✓ Создан маппинг для {len(nm_to_vendor)} товаров")
        
        # Для теста запрашиваем все товары батчами (лимит API - 20 за раз)
        print(f"   📊 Всего товаров: {len(nm_ids)}")
        print(f"   ⚠ API лимит: 20 товаров за запрос, запросим несколько батчей для поиска просмотров")
    except Exception as e:
        print(f"   ✗ Ошибка при получении списка товаров: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print(f"\n   Запрос детализированной статистики просмотров...")
    # Запрашиваем батчами по 20 товаров, чтобы найти все просмотры
    all_views_stats = {}
    
    batch_size = 20
    total_batches = (len(nm_ids) + batch_size - 1) // batch_size
    
    print(f"   📦 Будет обработано батчей: {total_batches} (по {batch_size} товаров)")
    print(f"   ⏱ Это займет примерно {total_batches * 5 / 60:.1f} минут с учетом задержек")
    
    # Обрабатываем все товары, не ограничиваем для теста
    for i in range(0, len(nm_ids), batch_size):
        batch_nm_ids = nm_ids[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        
        # Пропускаем если это не первый батч (чтобы избежать rate limiting)
        if i >= batch_size:
            import time
            delay = 5  # Увеличена задержка до 5 секунд
            print(f"   ⏳ Задержка {delay} секунд перед следующим батчем (избегаем rate limiting)...")
            time.sleep(delay)
        
        print(f"   Запрос батча {batch_num} ({len(batch_nm_ids)} товаров)...")
        batch_stats = analytics_client.get_product_views_detailed_for_date(yesterday, nm_ids=batch_nm_ids)
        
        # Объединяем результаты
        for key, value in batch_stats.items():
            if key in all_views_stats:
                all_views_stats[key] += value
            else:
                all_views_stats[key] = value
        
        # Если нашли просмотры в этом батче, продолжаем дальше
        if batch_stats:
            print(f"   ✓ В батче {batch_num} найдено просмотров: {sum(batch_stats.values())}")
    
    views_stats = all_views_stats
    
    # Заменяем nmId_* на vendorCode если есть маппинг
    if 'nm_to_vendor' in locals():
        final_stats = {}
        for key, value in views_stats.items():
            if key.startswith("nmId_"):
                nm_id = int(key.replace("nmId_", ""))
                vendor_code = nm_to_vendor.get(nm_id, key)
                final_stats[vendor_code] = value
            else:
                final_stats[key] = value
        views_stats = final_stats
    
    # Заменяем nmId_* на vendorCode если есть маппинг
    if 'nm_to_vendor' in locals():
        final_stats = {}
        for key, value in views_stats.items():
            if key.startswith("nmId_"):
                nm_id = int(key.replace("nmId_", ""))
                vendor_code = nm_to_vendor.get(nm_id, key)
                final_stats[vendor_code] = value
            else:
                final_stats[key] = value
        views_stats = final_stats
    print(f"   ✓ Получено данных: {len(views_stats)} карточек с просмотрами")
    
    if views_stats:
        print("\n   Примеры данных:")
        sorted_stats = sorted(views_stats.items(), key=lambda x: x[1], reverse=True)
        for vendor_code, count in sorted_stats[:5]:
            print(f"     {vendor_code}: {count} просмотров")
    else:
        print("   ⚠ Просмотров не найдено")
        print("   Проверьте логи выше для детальной информации о структуре ответа API")
        
except Exception as e:
    print(f"   ✗ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 4. Тест форматирования отчета
print("\n4. Тест форматирования отчета...")
try:
    from telegram import TelegramBot
    bot = TelegramBot(config.telegram_bot_token, config.telegram_chat_id)
    
    # Пробуем получить chat_id из БД
    if not bot.chat_id:
        from database import DatabaseManager
        db = DatabaseManager(config.db_path)
        saved_chat_id = db.get_setting("telegram_chat_id")
        if saved_chat_id:
            bot.chat_id = saved_chat_id
            print(f"   ✓ Chat ID получен из БД: {saved_chat_id}")
        else:
            print("   ⚠ Chat ID не найден - отчет не будет отправлен, только показан")
    
    # Форматируем отчет
    message = bot.format_product_views_report(views_stats, yesterday)
    print("\n   Отформатированный отчет:")
    print("   " + "-" * 56)
    for line in message.split('\n'):
        print(f"   {line}")
    print("   " + "-" * 56)
    
except Exception as e:
    print(f"   ✗ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 5. Тест отправки (если есть chat_id)
if bot.chat_id and views_stats:
    print("\n5. Тест отправки в Telegram...")
    try:
        result = bot.send_product_views_report(views_stats, yesterday)
        if result:
            print("   ✓ Отчет успешно отправлен в Telegram!")
        else:
            print("   ✗ Не удалось отправить отчет")
    except Exception as e:
        print(f"   ✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 60)
print("Тест завершен!")
print("=" * 60)
print("\nЕсли данные получены, но отчет не отправляется автоматически,")
print("проверьте логи бота в 00:05 UTC для отладки.")
