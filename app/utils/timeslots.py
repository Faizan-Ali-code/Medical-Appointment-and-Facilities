"""Dates, times and appointment slots."""
import datetime


def now():
    """The current local date and time. Everything asks here, so tests can set the clock."""
    return datetime.datetime.now()


def today():
    return now().date()


def parse_date(text):
    """'2025-03-14' -> datetime.date, or None if the text is not a date."""
    try:
        return datetime.date.fromisoformat((text or '').strip())
    except ValueError:
        return None


def parse_time(text):
    """'14:30' -> datetime.time, or None if the text is not a time."""
    try:
        return datetime.datetime.strptime((text or '').strip(), '%H:%M').time()
    except ValueError:
        return None


def format_time(value):
    """datetime.time -> '02:30 PM'."""
    return value.strftime('%I:%M %p')


def make_slots(start, end, minutes):
    """Start times of the slots of `minutes` length that fit between `start` and `end`."""
    if not (start and end and minutes and minutes > 0):
        return []
    day = datetime.date(2000, 1, 1)
    current, last = datetime.datetime.combine(day, start), datetime.datetime.combine(day, end)
    step = datetime.timedelta(minutes=minutes)
    slots = []
    while current + step <= last:
        slots.append(current.time())
        current += step
    return slots
