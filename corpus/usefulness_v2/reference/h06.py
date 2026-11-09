import datetime


def _check(value):
    if isinstance(value, datetime.datetime) or not isinstance(value, datetime.date):
        raise TypeError("expected a datetime.date")


def _is_business_day(day, holidays):
    return day.weekday() < 5 and day not in holidays


def business_days(start, end, holidays=()):
    _check(start)
    _check(end)
    holidays = set(holidays)
    if end < start:
        return -business_days(end, start, holidays)
    count = 0
    day = start
    while day < end:
        if _is_business_day(day, holidays):
            count += 1
        day += datetime.timedelta(days=1)
    return count


def add_business_days(start, n, holidays=()):
    _check(start)
    holidays = set(holidays)
    step = datetime.timedelta(days=1 if n >= 0 else -1)
    remaining = abs(n)
    day = start
    while remaining:
        day += step
        if _is_business_day(day, holidays):
            remaining -= 1
    return day
