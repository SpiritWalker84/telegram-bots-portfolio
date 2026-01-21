"""Bot handlers."""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery
from aiogram.filters import Command
import logging

from src.services.payment_service import PaymentService
from src.services.user_service import UserService
from src.utils.keyboards import main_menu, buy_btn
from src.utils.material_loader import MaterialLoader

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("start"))
async def cmd_start(
    message: Message,
    bot: Bot,
    user_service: UserService,
    payment_service: PaymentService,
    channel_id: str,
    course_price: int = 990
) -> None:
    """Handle /start command."""
    user_id = message.from_user.id
    
    try:
        await user_service.register_user(user_id)
        
        # Check if user already paid
        is_paid = await user_service.check_payment_status(user_id)
        
        if is_paid:
            # Create invite link for paid user
            try:
                invite_link = await payment_service.create_invite_link(
                    bot, channel_id, user_id
                )
                
                if invite_link:
                    await message.answer(
                        f"👋 Добро пожаловать обратно!\n\n"
                        f"🔗 Ваша ссылка для доступа к курсу:\n{invite_link}",
                        reply_markup=main_menu(course_price)
                    )
                else:
                    await message.answer(
                        "👋 Добро пожаловать обратно!\n\n"
                        "Вы уже оплатили курс. Обратитесь к администратору для получения доступа.",
                        reply_markup=main_menu(course_price)
                    )
            except Exception as e:
                logger.error(f"Error creating invite link for paid user {user_id}: {e}")
                await message.answer(
                    "👋 Добро пожаловать обратно!\n\n"
                    "Вы уже оплатили курс. Обратитесь к администратору для получения доступа.",
                    reply_markup=main_menu(course_price)
                )
        else:
            await message.answer(
                "👋 Добро пожаловать!\n\n"
                "Выберите действие:",
                reply_markup=main_menu(course_price)
            )
    except Exception as e:
        logger.error(f"Error in /start handler: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")


@router.message(Command("trial"))
async def cmd_trial(message: Message, course_price: int = 990) -> None:
    """Handle /trial command."""
    try:
        loader = MaterialLoader()
        trial_content = loader.load_trial_lesson()
        
        await message.answer(
            trial_content,
            reply_markup=buy_btn(course_price)
        )
    except FileNotFoundError:
        await message.answer(
            "📚 Пробный урок временно недоступен.\n\n"
            "Но вы можете приобрести полный курс прямо сейчас!",
            reply_markup=buy_btn(course_price)
        )
    except Exception as e:
        logger.error(f"Error in /trial handler: {e}")
        await message.answer("Произошла ошибка при загрузке пробного урока.")


@router.callback_query(F.data == "trial")
async def callback_trial(callback: CallbackQuery, course_price: int = 990) -> None:
    """Handle trial button callback."""
    try:
        loader = MaterialLoader()
        trial_content = loader.load_trial_lesson()
        
        await callback.message.edit_text(
            trial_content,
            reply_markup=buy_btn(course_price)
        )
        await callback.answer()
    except FileNotFoundError:
        await callback.message.edit_text(
            "📚 Пробный урок временно недоступен.\n\n"
            "Но вы можете приобрести полный курс прямо сейчас!",
            reply_markup=buy_btn(course_price)
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in trial callback: {e}")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data == "buy_course")
async def callback_buy_course(
    callback: CallbackQuery,
    bot: Bot,
    payment_service: PaymentService
) -> None:
    """Handle buy course button callback."""
    
    try:
        await payment_service.send_invoice(bot, callback.from_user.id)
        await callback.answer()
    except ValueError as e:
        error_msg = str(e)
        logger.error(f"Error in buy_course callback: {error_msg}")
        await callback.answer(
            "❌ Ошибка: токен провайдера не настроен.\n\n"
            "Проверьте .env файл и настройте PROVIDER_TOKEN.\n"
            "См. файл PAYMENT_SETUP.md для инструкций.",
            show_alert=True
        )
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error in buy_course callback: {e}")
        
        # More user-friendly error messages
        if "PAYMENT_PROVIDER_INVALID" in error_msg:
            await callback.answer(
                "❌ Ошибка: неверный токен провайдера.\n\n"
                "Нужен токен для Telegram Payments из личного кабинета ЮKassa.\n"
                "См. файл PAYMENT_SETUP.md для инструкций.",
                show_alert=True
            )
        else:
            await callback.answer("Ошибка при создании счета. Попробуйте позже.", show_alert=True)


@router.pre_checkout_query()
async def pre_checkout_handler(
    pre_checkout_query: PreCheckoutQuery,
    bot: Bot,
    payment_service: PaymentService
) -> None:
    """Handle pre-checkout query."""
    await payment_service.process_pre_checkout(pre_checkout_query, bot)


@router.message(F.successful_payment)
async def successful_payment_handler(
    message: Message,
    bot: Bot,
    user_service: UserService,
    payment_service: PaymentService,
    channel_id: str
) -> None:
    """Handle successful payment."""
    
    user_id = message.from_user.id
    
    invite_link = await user_service.process_payment(
        user_id, bot, channel_id, payment_service
    )
    
    if invite_link:
        await message.answer(
            f"✅ Оплата успешно получена!\n\n"
            f"🔗 Ваша ссылка для доступа к курсу:\n{invite_link}\n\n"
            f"Ссылка одноразовая, используйте её для входа в канал с курсом."
        )
    else:
        logger.warning(f"Could not create invite link for user {user_id}. Channel: {channel_id}")
        await message.answer(
            f"✅ Оплата успешно получена!\n\n"
            f"⚠️ Внимание: не удалось автоматически создать ссылку для доступа.\n\n"
            f"Ваш платеж зарегистрирован в системе. "
            f"Обратитесь к администратору для получения доступа к курсу.\n\n"
            f"Ваш ID: {user_id}"
        )
