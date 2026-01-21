"""FSM states for booking-bot."""

from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    waiting_for_service = State()
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_notes = State()
    waiting_for_confirmation = State()


class AdminStates(StatesGroup):
    adding_service_name = State()
    adding_service_duration = State()
    adding_service_price = State()
    adding_service_description = State()
    editing_service_value = State()
    setting_working_hours_start = State()
    setting_working_hours_end = State()
    setting_appointment_interval = State()

