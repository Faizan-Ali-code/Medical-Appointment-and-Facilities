"""Appointment time slots: doctors' slots are stored as text ('10:00 AM'); these helpers give them a real time."""
import datetime

_FORMATS = ('%I:%M %p', '%I:%M%p', '%H:%M')


def parse_slot(text):
    """'10:00 AM' / '10:00am' / '14:30' -> datetime.time, or None if the text is not a time."""
    value = (text or '').strip().upper()
    for fmt in _FORMATS:
        try:
            return datetime.datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    return None


def format_slot(value):
    """datetime.time -> '09:30 AM' (the one format the admin form stores)."""
    return value.strftime('%I:%M %p')


def sort_key(text):
    """Order slots by time of day; text that is not a time goes last, in its original order."""
    parsed = parse_slot(text)
    return (parsed is None, parsed or datetime.time.min)


def has_passed(date, slot, now=None):
    """True for a slot earlier today than `now` (the server's local time)."""
    now = now or datetime.datetime.now()
    parsed = parse_slot(slot)
    return date == now.date() and parsed is not None and parsed <= now.time()
