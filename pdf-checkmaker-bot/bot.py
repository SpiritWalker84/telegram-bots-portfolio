"""
Telegram бот для генерации PDF-чеков из файлов данных и HTML шаблонов.
"""

import asyncio
import io
import logging
import os
from pathlib import Path
from typing import Optional

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    Document,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from dotenv import load_dotenv

from src.pdf_generator import generate_receipt_pdf

# Загружаем переменные окружения
load_dotenv()


def escape_html(text: str) -> str:
    """Экранирует специальные символы HTML для безопасного отображения в Telegram."""
    if not isinstance(text, str):
        text = str(text)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Получаем токен и ID администратора из .env
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env файле!")

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()


# Состояния FSM
class ReceiptStates(StatesGroup):
    waiting_for_data_file = State()
    waiting_for_template = State()
    ready_to_generate = State()


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором."""
    if not ADMIN_ID:
        return True  # Если ADMIN_ID не указан, разрешаем всем
    try:
        return int(ADMIN_ID) == user_id
    except ValueError:
        return False


def get_main_keyboard(data_loaded: bool = False, template_loaded: bool = False) -> InlineKeyboardMarkup:
    """Создает главную клавиатуру с кнопками."""
    keyboard = []
    
    # Кнопка загрузки данных
    data_text = "✅ Данные загружены" if data_loaded else "📄 Загрузить файл данных"
    keyboard.append([InlineKeyboardButton(
        text=data_text,
        callback_data="load_data_file"
    )])
    
    # Кнопка загрузки шаблона
    template_text = "✅ Шаблон загружен" if template_loaded else "📝 Загрузить шаблон HTML"
    keyboard.append([InlineKeyboardButton(
        text=template_text,
        callback_data="load_template"
    )])
    
    # Кнопка просмотра подготовленных данных
    keyboard.append([InlineKeyboardButton(
        text="👁 Просмотр подготовленных данных",
        callback_data="view_data"
    )])
    
    # Кнопка преобразования (активна только когда оба файла загружены)
    if data_loaded and template_loaded:
        keyboard.append([InlineKeyboardButton(
            text="🔄 Преобразовать в PDF",
            callback_data="generate_pdf"
        )])
    else:
        keyboard.append([InlineKeyboardButton(
            text="⏳ Преобразовать в PDF (загрузите оба файла)",
            callback_data="generate_pdf_disabled"
        )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start."""
    # Очищаем состояние
    await state.clear()
    
    welcome_text = """
👋 <b>Добро пожаловать в PDF-генератор чеков!</b>

Я могу создать PDF-чек из ваших данных.

<b>Как использовать:</b>
1️⃣ Загрузите файл с данными (CSV, JSON или Excel)
2️⃣ Загрузите HTML шаблон для чека
3️⃣ Нажмите "Преобразовать в PDF"
4️⃣ Скачайте готовый PDF-чек!

<b>Поддерживаемые форматы данных:</b>
• CSV (UTF-8, CP1251)
• JSON
• Excel (.xlsx)

Используйте кнопки ниже для работы с ботом.
"""
    await message.answer(
        welcome_text,
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help."""
    help_text = """
📖 <b>Справка по использованию бота</b>

<b>Процесс генерации чека:</b>
1. Используйте команду /generate
2. Отправьте файл с данными (CSV/JSON/Excel)
3. Отправьте HTML шаблон
4. Получите PDF-чек!

<b>Формат данных CSV:</b>
<code>name,price,quantity
Товар 1,100.50,2
Товар 2,200.75,1</code>

<b>Формат данных JSON:</b>
<code>[
  {"name": "Товар 1", "price": 100.50, "quantity": 2},
  {"name": "Товар 2", "price": 200.75, "quantity": 1}
]</code>

<b>HTML шаблон:</b>
Используйте Jinja2 синтаксис. Доступные переменные:
• <code>items</code> - список товаров
• <code>receipt_id</code> - ID чека
• <code>total</code> - общая сумма

<b>Пример HTML шаблона:</b>
<code>&lt;html&gt;
&lt;head&gt;
  &lt;style&gt;
    @page { size: A6; margin: 5mm; }
    table { width: 100%; }
  &lt;/style&gt;
&lt;/head&gt;
&lt;body&gt;
  &lt;h2&gt;Чек #{{ receipt_id }}&lt;/h2&gt;
  &lt;table&gt;
    {% for item in items %}
    &lt;tr&gt;
      &lt;td&gt;{{ item.name }}&lt;/td&gt;
      &lt;td&gt;{{ item.price }}&lt;/td&gt;
    &lt;/tr&gt;
    {% endfor %}
  &lt;/table&gt;
&lt;/body&gt;
&lt;/html&gt;</code>
"""
    await message.answer(help_text, parse_mode="HTML")


@router.callback_query(F.data == "load_data_file")
async def callback_load_data(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки загрузки файла данных."""
    await callback.answer()
    await state.set_state(ReceiptStates.waiting_for_data_file)
    await callback.message.edit_text(
        "📄 <b>Загрузка файла данных</b>\n\n"
        "Отправьте файл с данными:\n"
        "• CSV (.csv)\n"
        "• JSON (.json)\n"
        "• Excel (.xlsx, .xls)\n\n"
        "Или нажмите /cancel для отмены",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "load_template")
async def callback_load_template(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки загрузки шаблона."""
    await callback.answer()
    await state.set_state(ReceiptStates.waiting_for_template)
    await callback.message.edit_text(
        "📝 <b>Загрузка HTML шаблона</b>\n\n"
        "Отправьте HTML файл (.html, .htm) или текст с HTML кодом.\n\n"
        "Или нажмите /cancel для отмены",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "view_data")
async def callback_view_data(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки просмотра подготовленных данных."""
    await callback.answer()
    data = await state.get_data()
    
    data_file_name = data.get("data_file_name", "Не загружено")
    template_file_name = data.get("template_file_name", "Не загружено")
    
    data_loaded = data.get("data_bytes") is not None
    template_loaded = data.get("template_bytes") is not None
    
    # Парсим данные для показа структуры
    data_structure = ""
    if data_loaded:
        try:
            from src.file_parser import parse_file
            data_bytes = data.get("data_bytes")
            file_type = data.get("data_file_type", "csv")
            if file_type == "xls":
                file_type = "xlsx"
            
            parsed_data = parse_file(data_bytes, file_type)
            if parsed_data:
                keys = list(parsed_data[0].keys())
                data_structure = f"\n\n📋 <b>Структура данных:</b>\n"
                data_structure += f"   Ключи: <code>{', '.join(escape_html(str(k)) for k in keys)}</code>\n"
                data_structure += f"   Записей: {len(parsed_data)}\n"
                data_structure += f"   Первая запись: <code>{escape_html(str(parsed_data[0]))}</code>"
        except Exception as e:
            data_structure = f"\n\n⚠️ Не удалось проанализировать данные: {escape_html(str(e))}"
    
    status_text = f"""
📊 <b>Подготовленные данные:</b>

📄 <b>Данные:</b> <code>{escape_html(data_file_name)}</code>
📝 <b>Шаблон:</b> <code>{escape_html(template_file_name)}</code>
{data_structure}

{"✅ Оба файла загружены! Можно преобразовывать." if (data_loaded and template_loaded) else "⚠️ Загрузите оба файла для продолжения."}
"""
    
    await callback.message.edit_text(
        status_text,
        parse_mode="HTML",
        reply_markup=get_main_keyboard(data_loaded, template_loaded)
    )


@router.callback_query(F.data == "generate_pdf_disabled")
async def callback_generate_disabled(callback: CallbackQuery):
    """Обработчик кнопки преобразования когда файлы не загружены."""
    await callback.answer(
        "⚠️ Сначала загрузите оба файла (данные и шаблон)!",
        show_alert=True
    )


@router.callback_query(F.data == "generate_pdf")
async def callback_generate_pdf(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки преобразования в PDF."""
    await callback.answer()
    
    data = await state.get_data()
    data_bytes = data.get("data_bytes")
    template_bytes = data.get("template_bytes")
    
    if not data_bytes or not template_bytes:
        await callback.answer(
            "❌ Файлы не загружены!",
            show_alert=True
        )
        return
    
    try:
        # Отправляем сообщение о начале генерации
        await callback.message.edit_text("⏳ Генерирую PDF-чек...")
        
        # Определяем тип файла
        file_type = data.get("data_file_type")
        if file_type == "xls":
            file_type = "xlsx"
        
        # Генерируем ID чека
        receipt_id = f"RECEIPT-{callback.from_user.id}-{callback.message.message_id}"
        
        # Генерируем PDF
        pdf_bytes, error = generate_receipt_pdf(
            data_bytes=data_bytes,
            html_template_bytes=template_bytes,
            receipt_id=receipt_id,
            file_type=file_type
        )
        
        if error:
            await callback.message.edit_text(
                f"❌ <b>Ошибка генерации PDF:</b>\n\n"
                f"<code>{escape_html(error)}</code>\n\n"
                "Попробуйте загрузить файлы заново.",
                parse_mode="HTML",
                reply_markup=get_main_keyboard(True, True)
            )
            return
        
        # Отправляем PDF пользователю
        pdf_input_file = BufferedInputFile(
            file=pdf_bytes,
            filename=f"receipt_{receipt_id}.pdf"
        )
        
        await callback.message.answer_document(
            document=pdf_input_file,
            caption=f"✅ <b>PDF-чек готов!</b>\n\n"
                   f"ID чека: <code>{escape_html(receipt_id)}</code>\n"
                   f"Размер: {len(pdf_bytes)} байт\n\n"
                   f"Используйте /start для создания нового чека.",
            parse_mode="HTML"
        )
        
        await callback.message.edit_text(
            "✅ PDF-чек успешно создан и отправлен!",
            reply_markup=get_main_keyboard(True, True)
        )
        
        logger.info(f"PDF успешно сгенерирован для пользователя {callback.from_user.id}")
        
    except Exception as e:
        logger.error(f"Ошибка при генерации PDF: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ <b>Неожиданная ошибка:</b>\n\n"
            f"<code>{escape_html(str(e))}</code>\n\n"
            "Попробуйте еще раз.",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(True, True)
        )


@router.message(StateFilter(ReceiptStates.waiting_for_data_file), F.document)
async def process_data_file(message: Message, state: FSMContext):
    """Обрабатывает файл с данными."""
    document: Document = message.document
    
    # Проверяем тип файла
    file_name = document.file_name or ""
    file_ext = Path(file_name).suffix.lower()
    
    allowed_extensions = {".csv", ".json", ".xlsx", ".xls"}
    if file_ext not in allowed_extensions:
        await message.answer(
            "❌ <b>Неподдерживаемый формат файла!</b>\n\n"
            "Поддерживаются только:\n"
            "• CSV (.csv)\n"
            "• JSON (.json)\n"
            "• Excel (.xlsx, .xls)\n\n"
            "Попробуйте отправить файл правильного формата.",
            parse_mode="HTML"
        )
        return
    
    try:
        # Скачиваем файл
        file = await bot.get_file(document.file_id)
        file_bytes = await bot.download_file(file.file_path)
        data_bytes = file_bytes.read()
        
        # Определяем тип файла
        file_type = file_ext[1:] if file_ext.startswith(".") else file_ext
        if file_type == "xls":
            file_type = "xlsx"
        
        # Сохраняем данные в состояние
        await state.update_data(
            data_bytes=data_bytes,
            data_file_name=file_name,
            data_file_type=file_type
        )
        
        # Проверяем, загружен ли шаблон
        data = await state.get_data()
        template_loaded = data.get("template_bytes") is not None
        
        await message.answer(
            f"✅ <b>Файл данных загружен!</b>\n\n"
            f"📄 Файл: <code>{escape_html(file_name)}</code>\n"
            f"📊 Формат: {escape_html(file_type.upper())}\n"
            f"💾 Размер: {len(data_bytes)} байт\n\n"
            f"{'✅ Оба файла загружены! Можно преобразовывать.' if template_loaded else '📝 Теперь загрузите HTML шаблон.'}",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(data_loaded=True, template_loaded=template_loaded)
        )
        
        # Возвращаемся в основное состояние
        await state.set_state(ReceiptStates.ready_to_generate)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке файла данных: {e}", exc_info=True)
        await message.answer(
            f"❌ <b>Ошибка при обработке файла:</b>\n\n"
            f"<code>{escape_html(str(e))}</code>\n\n"
            "Попробуйте отправить файл снова.",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
        await state.set_state(ReceiptStates.ready_to_generate)


@router.message(StateFilter(ReceiptStates.waiting_for_template), F.document)
async def process_template_file(message: Message, state: FSMContext):
    """Обрабатывает HTML шаблон (файл)."""
    document: Document = message.document
    
    file_name = document.file_name or ""
    file_ext = Path(file_name).suffix.lower()
    
    if file_ext not in {".html", ".htm"}:
        await message.answer(
            "❌ <b>Неподдерживаемый формат!</b>\n\n"
            "Файл шаблона должен быть HTML:\n"
            "• .html\n"
            "• .htm\n\n"
            "Попробуйте отправить файл правильного формата.",
            parse_mode="HTML"
        )
        return
    
    try:
        # Скачиваем шаблон
        file = await bot.get_file(document.file_id)
        file_bytes = await bot.download_file(file.file_path)
        template_bytes = file_bytes.read()
        
        # Сохраняем шаблон в состояние
        await state.update_data(
            template_bytes=template_bytes,
            template_file_name=file_name
        )
        
        # Проверяем, загружены ли данные
        data = await state.get_data()
        data_loaded = data.get("data_bytes") is not None
        
        await message.answer(
            f"✅ <b>HTML шаблон загружен!</b>\n\n"
            f"📝 Файл: <code>{escape_html(file_name)}</code>\n"
            f"💾 Размер: {len(template_bytes)} байт\n\n"
            f"{'✅ Оба файла загружены! Можно преобразовывать.' if data_loaded else '📄 Теперь загрузите файл с данными.'}",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(data_loaded=data_loaded, template_loaded=True)
        )
        
        # Возвращаемся в основное состояние
        await state.set_state(ReceiptStates.ready_to_generate)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке шаблона: {e}", exc_info=True)
        await message.answer(
            f"❌ <b>Ошибка при обработке файла:</b>\n\n"
            f"<code>{escape_html(str(e))}</code>\n\n"
            "Попробуйте отправить файл снова.",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
        await state.set_state(ReceiptStates.ready_to_generate)


@router.message(StateFilter(ReceiptStates.waiting_for_template), F.text)
async def process_template_text(message: Message, state: FSMContext):
    """Обрабатывает HTML шаблон, отправленный как текст."""
    try:
        template_text = message.text or message.html_text or ""
        template_bytes = template_text.encode("utf-8")
        
        # Сохраняем шаблон в состояние
        await state.update_data(
            template_bytes=template_bytes,
            template_file_name="Текст HTML"
        )
        
        # Проверяем, загружены ли данные
        data = await state.get_data()
        data_loaded = data.get("data_bytes") is not None
        
        await message.answer(
            f"✅ <b>HTML шаблон загружен!</b>\n\n"
            f"📝 Источник: Текст\n"
            f"💾 Размер: {len(template_bytes)} байт\n\n"
            f"{'✅ Оба файла загружены! Можно преобразовывать.' if data_loaded else '📄 Теперь загрузите файл с данными.'}",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(data_loaded=data_loaded, template_loaded=True)
        )
        
        # Возвращаемся в основное состояние
        await state.set_state(ReceiptStates.ready_to_generate)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке шаблона: {e}", exc_info=True)
        await message.answer(
            f"❌ <b>Ошибка при обработке шаблона:</b>\n\n"
            f"<code>{escape_html(str(e))}</code>\n\n"
            "Попробуйте отправить шаблон снова.",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
        await state.set_state(ReceiptStates.ready_to_generate)


@router.message(StateFilter(ReceiptStates.waiting_for_data_file))
async def wrong_data_file(message: Message):
    """Обрабатывает неправильный ввод на этапе ожидания файла данных."""
    await message.answer(
        "❌ <b>Ожидается файл с данными!</b>\n\n"
        "Отправьте файл формата:\n"
        "• CSV (.csv)\n"
        "• JSON (.json)\n"
        "• Excel (.xlsx, .xls)\n\n"
        "Или используйте /start для возврата в меню.",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )


@router.message(StateFilter(ReceiptStates.waiting_for_template))
async def wrong_template(message: Message):
    """Обрабатывает неправильный ввод на этапе ожидания шаблона."""
    await message.answer(
        "❌ <b>Ожидается HTML шаблон!</b>\n\n"
        "Отправьте:\n"
        "• HTML файл (.html, .htm)\n"
        "• Или текст с HTML кодом\n\n"
        "Или используйте /start для возврата в меню.",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )


@router.message(StateFilter(ReceiptStates.ready_to_generate))
async def ready_state_message(message: Message, state: FSMContext):
    """Обрабатывает сообщения в состоянии готовности."""
    data = await state.get_data()
    data_loaded = data.get("data_bytes") is not None
    template_loaded = data.get("template_bytes") is not None
    
    await message.answer(
        "💡 Используйте кнопки меню для работы с ботом.",
        reply_markup=get_main_keyboard(data_loaded, template_loaded)
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Отменяет текущую операцию."""
    await state.clear()
    await message.answer(
        "❌ Операция отменена.\n\n"
        "Используйте /start для начала работы.",
        reply_markup=get_main_keyboard()
    )


@router.message()
async def unknown_message(message: Message, state: FSMContext):
    """Обрабатывает неизвестные сообщения."""
    data = await state.get_data()
    data_loaded = data.get("data_bytes") is not None
    template_loaded = data.get("template_bytes") is not None
    
    await message.answer(
        "🤔 Я не понимаю эту команду.\n\n"
        "Используйте /start для начала работы или /help для справки.",
        reply_markup=get_main_keyboard(data_loaded, template_loaded)
    )


async def main():
    """Главная функция запуска бота."""
    # Регистрируем роутер
    dp.include_router(router)
    
    # Удаляем webhook если он был установлен (для избежания конфликтов)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook удален (если был установлен)")
    except Exception as e:
        logger.warning(f"Не удалось удалить webhook: {e}")
    
    logger.info("Бот запущен!")
    
    # Запускаем polling
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)

