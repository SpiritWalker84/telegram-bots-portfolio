"""Inline keyboards for bot."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def trial_btn() -> InlineKeyboardMarkup:
    """Trial lesson button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Пробный урок", callback_data="trial")]
        ]
    )


def buy_btn() -> InlineKeyboardMarkup:
    """Buy course button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 Купить курс (990₽)", callback_data="buy_course")]
        ]
    )


def main_menu() -> InlineKeyboardMarkup:
    """Main menu with trial and buy buttons."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Пробный урок", callback_data="trial")],
            [InlineKeyboardButton(text="💰 Купить курс (990₽)", callback_data="buy_course")],
        ]
    )

