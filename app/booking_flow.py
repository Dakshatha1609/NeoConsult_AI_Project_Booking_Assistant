from dataclasses import dataclass, field
from typing import Optional, Dict
from utils.validators import (
    is_valid_email,
    parse_booking_date,
    parse_booking_time,
)

BOOKING_FIELDS = ["name", "company", "email", "phone", "booking_type", "date", "time"]


@dataclass
class BookingState:
    name: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    booking_type: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    pending_confirmation: bool = False
    completed: bool = False
    meta: Dict = field(default_factory=dict)


def detect_intent(message: str) -> str:
    """
    Very simple rule-based intent detection:
    - 'booking' for booking-related messages
    - 'booking_lookup' for 'my bookings' style
    - 'general' otherwise (RAG)
    """
    msg = message.lower()
    booking_keywords = ["book", "booking", "consultation", "project call", "schedule", "slot"]
    lookup_keywords = ["my booking", "my bookings", "booking status"]

    if any(k in msg for k in lookup_keywords):
        return "booking_lookup"
    if any(k in msg for k in booking_keywords):
        return "booking"
    return "general"


def get_missing_field(state: BookingState) -> Optional[str]:
    """Return the next field that is still empty."""
    for field_name in BOOKING_FIELDS:
        if getattr(state, field_name) in [None, ""]:
            return field_name
    return None


def validate_and_set_field(state: BookingState, field_name: str, user_value: str):
    """
    Validate the value for a given field and update state.
    Return error message string if invalid, else None.
    """
    user_value = user_value.strip()

    if field_name == "email":
        if not is_valid_email(user_value):
            return "That doesn't look like a valid email. Please enter a valid email address."
        state.email = user_value

    elif field_name == "date":
        date_obj = parse_booking_date(user_value)
        if date_obj is None:
            return "Please enter date as YYYY-MM-DD."
        state.date = user_value
        state.meta["date_obj"] = date_obj

    elif field_name == "time":
        time_obj = parse_booking_time(user_value)
        if time_obj is None:
            return "Please enter time as HH:MM in 24-hour format."
        state.time = user_value
        state.meta["time_obj"] = time_obj

    else:
        setattr(state, field_name, user_value)

    return None


def summarize_booking(state: BookingState) -> str:
    """Return a confirmation message summarizing the booking."""
    return (
        "Please confirm your project consultation booking details:\n"
        f"- Contact Name: {state.name}\n"
        f"- Company: {state.company}\n"
        f"- Email: {state.email}\n"
        f"- Phone: {state.phone}\n"
        f"- Project Type: {state.booking_type}\n"
        f"- Preferred Date: {state.date}\n"
        f"- Preferred Time: {state.time}\n\n"
        "Reply 'yes' to confirm or 'no' to cancel."
    )
