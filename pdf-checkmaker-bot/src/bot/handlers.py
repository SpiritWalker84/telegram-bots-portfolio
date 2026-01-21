"""Router-based handlers for pdf-checkmaker-bot (aiogram 3)."""

import logging
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    Document,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from src.pdf_generator import generate_receipt_pdf
from src.file_parser import parse_file

logger = logging.getLogger(__name__)

router = Router()


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


def get_main_keyboard(
    data_loaded: bool = False, template_loaded: bool = False
) -> InlineKeyboardMarkup:
    """Создает главную клавиатуру с кнопками."""
    keyboard = []

    # Кнопка загрузки данных
    data_text = "✅ Данные загружены" if data_loaded else "📄 Загрузить файл данных"
    keyboard.append(
        [
            InlineKeyboardButton(
                text=data_text,
                callback_data="load_data_file",
            )
        ]
    )

    # Кнопка загрузки шаблона
    template_text = (
        "✅ Шаблон загружен" if template_loaded else "📝 Загрузить шаблон HTML"
    )
    keyboard.append(
        [
            InlineKeyboardButton(
                text=template_text,
                callback_data="load_template",
            )
        ]
    )

    # Кнопка просмотра подготовленных данных
    keyboard.append(
        [
            InlineKeyboardButton(
                text="👁 Просмотр подготовленных данных",
                callback_data="view_data",
            )
        ]
    )

    # Кнопка преобразования (активна только когда оба файла загружены)
    if data_loaded and template_loaded:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="🔄 Преобразовать в PDF",
                    callback_data="generate_pdf",
                )
            ]
        )
    else:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="⏳ Преобразовать в PDF (загрузите оба файла)",
                    callback_data="generate_pdf_disabled",
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


class ReceiptStates(StatesGroup):
    """FSM состояния для загрузки данных и шаблона."""

    waiting_for_data_file = State()
    waiting_for_template = State()
    ready_to_generate = State()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Обработчик команды /start."""
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
        reply_markup=get_main_keyboard(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
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
"""
    await message.answer(help_text, parse_mode="HTML")


@router.callback_query(F.data == "load_data_file")
async def callback_load_data(callback: CallbackQuery, state: FSMContext) -> None:
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
        parse_mode="HTML",
    )


@router.callback_query(F.data == "load_template")
async def callback_load_template(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработчик кнопки загрузки шаблона."""
    await callback.answer()
    await state.set_state(ReceiptStates.waiting_for_template)
    await callback.message.edit_text(
        "📝 <b>Загрузка HTML шаблона</b>\n\n"
        "Отправьте HTML файл (.html, .htm) или текст с HTML кодом.\n\n"
        "Или нажмите /cancel для отмены",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "view_data")
async def callback_view_data(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработчик кнопки просмотра подготовленных данных."""
    await callback.answer()
    data = await state.get_data()

    data_file_name = data.get("data_file_name", "Не загружено")
    template_file_name = data.get("template_file_name", "Не загружено")

    data_loaded = data.get("data_bytes") is not None
    template_loaded = data.get("template_bytes") is not None

    data_structure = ""
    if data_loaded:
        try:
            data_bytes = data.get("data_bytes")
            file_type = data.get("data_file_type", "csv")
            if file_type == "xls":
                file_type = "xlsx"

            parsed_data = parse_file(data_bytes, file_type)
            if parsed_data:
                keys = list(parsed_data[0].keys())
                data_structure = "\n\n📋 <b>Структура данных:</b>\n"
                data_structure += (
                    "   Ключи: <code>"
                    + ", ".join(escape_html(str(k)) for k in keys)
                    + "</code>\n"
                )
                data_structure += f"   Записей: {len(parsed_data)}\n"
                data_structure += (
                    "   Первая запись: <code>"
                    f"{escape_html(str(parsed_data[0]))}"
                    "</code>"
                )
        except Exception as e:  # noqa: BLE001
            data_structure = (
                "\n\n⚠️ Не удалось проанализировать данные: "
                f"{escape_html(str(e))}"
            )

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
        reply_markup=get_main_keyboard(data_loaded, template_loaded),
    )


@router.callback_query(F.data == "generate_pdf_disabled")
async def callback_generate_disabled(callback: CallbackQuery) -> None:
    """Обработчик кнопки преобразования когда файлы не загружены."""
    await callback.answer(
        "⚠️ Сначала загрузите оба файла (данные и шаблон)!",
        show_alert=True,
    )


@router.callback_query(F.data == "generate_pdf")
async def callback_generate_pdf(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработчик кнопки преобразования в PDF."""
    await callback.answer()

    data = await state.get_data()
    data_bytes = data.get("data_bytes")
    template_bytes = data.get("template_bytes")

    if not data_bytes or not template_bytes:
        await callback.answer(
            "❌ Файлы не загружены!",
            show_alert=True,
        )
        return

    try:
        await callback.message.edit_text("⏳ Генерирую PDF-чек...")

        file_type = data.get("data_file_type")
        if file_type == "xls":
            file_type = "xlsx"

        receipt_id = (
            f"RECEIPT-{callback.from_user.id}-{callback.message.message_id}"
        )

        pdf_bytes, error = generate_receipt_pdf(
            data_bytes=data_bytes,
            html_template_bytes=template_bytes,
            receipt_id=receipt_id,
            file_type=file_type,
        )

        if error:
            await callback.message.edit_text(
                "❌ <b>Ошибка генерации PDF:</b>\n\n"
                f"<code>{escape_html(error)}</code>\n\n"
                "Попробуйте загрузить файлы заново.",
                parse_mode="HTML",
                reply_markup=get_main_keyboard(True, True),
            )
            return

        pdf_input_file = BufferedInputFile(
            file=pdf_bytes,
            filename=f"receipt_{receipt_id}.pdf",
        )

        await callback.message.answer_document(
            document=pdf_input_file,
            caption="✅ <b>PDF-чек готов!</b>\n\n"
            f"ID чека: <code>{escape_html(receipt_id)}</code>\n"
            f"Размер: {len(pdf_bytes)} байт\n\n"
            "Используйте /start для создания нового чека.",
            parse_mode="HTML",
        )

        await callback.message.edit_text(
            "✅ PDF-чек успешно создан и отправлен!",
            reply_markup=get_main_keyboard(True, True),
        )

        logger.info(
            "PDF успешно сгенерирован для пользователя %s",
            callback.from_user.id,
        )

    except Exception as e:  # noqa: BLE001
        logger.error("Ошибка при генерации PDF: %s", e, exc_info=True)
        await callback.message.edit_text(
            "❌ <b>Неожиданная ошибка:</b>\n\n"
            f"<code>{escape_html(str(e))}</code>\n\n"
            "Попробуйте еще раз.",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(True, True),
        )


@router.message(StateFilter(ReceiptStates.waiting_for_data_file), F.document)
async def process_data_file(message: Message, state: FSMContext) -> None:
    """Обрабатывает файл с данными."""
    document: Document = message.document

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
            parse_mode="HTML",
        )
        return

    try:
        file = await message.bot.get_file(document.file_id)
        file_bytes = await message.bot.download_file(file.file_path)
        data_bytes = file_bytes.read()

        file_type = file_ext[1:] if file_ext.startswith(".") else file_ext
        if file_type == "xls":
            file_type = "xlsx"

        await state.update_data(
            data_bytes=data_bytes,
            data_file_name=file_name,
            data_file_type=file_type,
        )

        data = await state.get_data()
        template_loaded = data.get("template_bytes") is not None

        await message.answer(
            "✅ <b>Файл данных загружен!</b>\n\n"
            f"📄 Файл: <code>{escape_html(file_name)}</code>\n"
            f"📊 Формат: {escape_html(file_type.upper())}\n"
            f"💾 Размер: {len(data_bytes)} байт\n\n"
            f"{'✅ Оба файла загружены! Можно преобразовывать.' if template_loaded else '📝 Теперь загрузите HTML шаблон.'}",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(
                data_loaded=True,
                template_loaded=template_loaded,
            ),
        )

        await state.set_state(ReceiptStates.ready_to_generate)

    except Exception as e:  # noqa: BLE001
        logger.error("Ошибка при обработке файла данных: %s", e, exc_info=True)
        await message.answer(
            "❌ <b>Ошибка при обработке файла:</b>\n\n"
            f"<code>{escape_html(str(e))}</code>\n\n"
            "Попробуйте отправить файл снова.",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(),
        )
        await state.set_state(ReceiptStates.ready_to_generate)


@router.message(StateFilter(ReceiptStates.waiting_for_template), F.document)
async def process_template_file(message: Message, state: FSMContext) -> None:
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
            parse_mode="HTML",
        )
        return

    try:
        file = await message.bot.get_file(document.file_id)
        file_bytes = await message.bot.download_file(file.file_path)
        template_bytes = file_bytes.read()

        await state.update_data(
            template_bytes=template_bytes,
            template_file_name=file_name,
        )

        data = await state.get_data()
        data_loaded = data.get("data_bytes") is not None

        await message.answer(
            "✅ <b>HTML шаблон загружен!</b>\n\n"
            f"📝 Файл: <code>{escape_html(file_name)}</code>\n"
            f"💾 Размер: {len(template_bytes)} байт\n\n"
            f"{'✅ Оба файла загружены! Можно преобразовывать.' if data_loaded else '📄 Теперь загрузите файл с данными.'}",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(
                data_loaded=data_loaded,
                template_loaded=True,
            ),
        )

        await state.set_state(ReceiptStates.ready_to_generate)

    except Exception as e:  # noqa: BLE001
        logger.error("Ошибка при обработке шаблона: %s", e, exc_info=True)
        await message.answer(
            "❌ <b>Ошибка при обработке файла:</b>\n\n"
            f"<code>{escape_html(str(e))}</code>\n\n"
            "Попробуйте отправить файл снова.",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(),
        )
        await state.set_state(ReceiptStates.ready_to_generate)


@router.message(StateFilter(ReceiptStates.waiting_for_template), F.text)
async def process_template_text(message: Message, state: FSMContext) -> None:
    """Обрабатывает HTML шаблон, отправленный как текст."""
    try:
        template_text = message.text or message.html_text or ""
        template_bytes = template_text.encode("utf-8")

        await state.update_data(
            template_bytes=template_bytes,
            template_file_name="Текст HTML",
        )

        data = await state.get_data()
        data_loaded = data.get("data_bytes") is not None

        await message.answer(
            "✅ <b>HTML шаблон загружен!</b>\n\n"
            "📝 Источник: Текст\n"
            f"💾 Размер: {len(template_bytes)} байт\n\n"
            f"{'✅ Оба файла загружены! Можно преобразовывать.' if data_loaded else '📄 Теперь загрузите файл с данными.'}",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(
                data_loaded=data_loaded,
                template_loaded=True,
            ),
        )

        await state.set_state(ReceiptStates.ready_to_generate)

    except Exception as e:  # noqa: BLE001
        logger.error("Ошибка при обработке шаблона: %s", e, exc_info=True)
        await message.answer(
            "❌ <b>Ошибка при обработке шаблона:</b>\n\n"
            f"<code>{escape_html(str(e))}</code>\n\n"
            "Попробуйте отправить шаблон снова.",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(),
        )
        await state.set_state(ReceiptStates.ready_to_generate)


@router.message(StateFilter(ReceiptStates.waiting_for_data_file))
async def wrong_data_file(message: Message) -> None:
    """Обрабатывает неправильный ввод на этапе ожидания файла данных."""
    await message.answer(
        "❌ <b>Ожидается файл с данными!</b>\n\n"
        "Отправьте файл формата:\n"
        "• CSV (.csv)\n"
        "• JSON (.json)\n"
        "• Excel (.xlsx, .xls)\n\n"
        "Или используйте /start для возврата в меню.",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(),
    )


@router.message(StateFilter(ReceiptStates.waiting_for_template))
async def wrong_template(message: Message) -> None:
    """Обрабатывает неправильный ввод на этапе ожидания шаблона."""
    await message.answer(
        "❌ <b>Ожидается HTML шаблон!</b>\n\n"
        "Отправьте:\n"
        "• HTML файл (.html, .htm)\n"
        "• Или текст с HTML кодом\n\n"
        "Или используйте /start для возврата в меню.",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(),
    )


@router.message(StateFilter(ReceiptStates.ready_to_generate))
async def ready_state_message(message: Message, state: FSMContext) -> None:
    """Обрабатывает сообщения в состоянии готовности."""
    data = await state.get_data()
    data_loaded = data.get("data_bytes") is not None
    template_loaded = data.get("template_bytes") is not None

    await message.answer(
        "💡 Используйте кнопки меню для работы с ботом.",
        reply_markup=get_main_keyboard(data_loaded, template_loaded),
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """Отменяет текущую операцию."""
    await state.clear()
    await message.answer(
        "❌ Операция отменена.\n\n"
        "Используйте /start для начала работы.",
        reply_markup=get_main_keyboard(),
    )


@router.message()
async def unknown_message(message: Message, state: FSMContext) -> None:
    """Обрабатывает неизвестные сообщения."""
    data = await state.get_data()
    data_loaded = data.get("data_bytes") is not None
    template_loaded = data.get("template_bytes") is not None

    await message.answer(
        "🤔 Я не понимаю эту команду.\n\n"
        "Используйте /start для начала работы или /help для справки.",
        reply_markup=get_main_keyboard(data_loaded, template_loaded),
    )

