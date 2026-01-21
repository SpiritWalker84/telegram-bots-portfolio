"""Inline keyboards for bot."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def trial_btn() -> InlineKeyboardMarkup:
    """Trial lesson button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Пробный урок", callback_data="trial")]
        ]
    )


def buy_btn(course_price: int = 990) -> InlineKeyboardMarkup:
    """
    Buy course button.
    
    Args:
        course_price: Course price in rubles
        
    Returns:
        InlineKeyboardMarkup with buy button
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"💰 Купить курс ({course_price}₽)", callback_data="buy_course")]
        ]
    )


def main_menu(course_price: int = 990) -> InlineKeyboardMarkup:
    """
    Main menu with trial and buy buttons.
    
    Args:
        course_price: Course price in rubles
        
    Returns:
        InlineKeyboardMarkup with main menu
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Пробный урок", callback_data="trial")],
            [InlineKeyboardButton(text=f"💰 Купить курс ({course_price}₽)", callback_data="buy_course")],
        ]
    )
