from email_validator import validate_email, EmailNotValidError
from datetime import datetime


def is_valid_email(email: str) -> bool:
    """Return True if email format is valid."""
    try:
        validate_email(email)
        return True
    except EmailNotValidError:
        return False


def parse_booking_date(date_str: str):
    """Parse date in strict YYYY-MM-DD format. Return date or None."""
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except Exception:
        return None


def parse_booking_time(time_str: str):
    """Parse time in strict HH:MM 24-hour format. Return time or None."""
    try:
        return datetime.strptime(time_str.strip(), "%H:%M").time()
    except Exception:
        return None
