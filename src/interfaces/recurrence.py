from dataclasses import dataclass
from datetime import date

from recurrence import FR, MO, MONTHLY, TH, TU, WE, WEEKLY
from recurrence import Recurrence as OriginalRecurrence
from recurrence import Rule, Weekday, deserialize

from meals.constants import RRULE_START

days_of_week = [
    None,
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]
abbreviated_days_of_week = [None] + \
    list(map(lambda i: i[:3], days_of_week[1:]))

weeks_of_month = [
    None,
    "First",
    "Second",
    "Third",
    "Fourth",
    "Fifth",
]
abbreviated_weeks_of_month = [None, "1st", "2nd", "3rd", "4th", "5th"]

months = [
    None,
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


@dataclass(frozen=True, eq=True)
class DayOfMonth:
    """
    Simple dataclass for containing the 2nd monday, 4th thursday etc.
    """

    day_of_week: int
    week_of_month: int

    def __str__(self):
        return day_of_month_to_text(self)


# these are the display names
# called titles because both words are capitalized
days_of_month_titles = {}
for week in range(len(weeks_of_month)):
    for day in range(len(days_of_week)):
        if weeks_of_month[week] is not None and days_of_week[day] is not None:
            days_of_month_titles[(
                day, week)] = f"{weeks_of_month[week]} {days_of_week[day]}"

# these are used as the field names in the recurrence forms
days_of_month_field_names = {}
days_of_month_tuples = {}
for week in range(len(weeks_of_month)):
    for day in range(len(days_of_week)):
        if weeks_of_month[week] is not None and days_of_week[day] is not None:
            field_name = f"{weeks_of_month[week].lower()}_{days_of_week[day].lower()}"
            # reverse lookup used for validation
            days_of_month_tuples[field_name] = DayOfMonth(day, week)
            # lookup used to create fields
            days_of_month_field_names[(day, week)] = field_name


# These are used in the create-assignment template to control column appearance
start_of_week_field_names = []
end_of_week_field_names = []
for key, value in days_of_month_field_names.items():
    if "monday" in value:
        start_of_week_field_names.append(value)
    elif "friday" in value:
        end_of_week_field_names.append(value)


def Recurrence(rrules, **kwargs):
    """
    Wrapper class for the actual pip installed Recurrence.

    Allows `rrules` to be a single rrule, and overrides the dtstart to be the
    global RRULE_START.
    """
    if not hasattr(rrules, "__iter__"):
        rrules = [rrules]
    kwargs["dtstart"] = RRULE_START
    return OriginalRecurrence(rrules=rrules, **kwargs)


def one_day_recurrence(day, which=None):
    """
    Utility function for making a quick recurrence for testing purposes.
    """
    if isinstance(day, Weekday):
        weekday = day
    else:
        weekday = Weekday(day, which)
    return Recurrence(Rule(freq=MONTHLY, byday=weekday), dtstart=RRULE_START)


def date_to_day_of_month(date):
    """
    Convert a python datetime.date object to a DayOfMonth object.
    """
    return DayOfMonth(date.isoweekday(), (date.day - 1) // 7 + 1)


def day_of_month_to_date(day_of_month, month, year):
    """
    Given a month and a year, convert a DayOfMonth object to a date.
    Usefull for realizing the actual jobs for a given volunteer and Assignment

    If the day of the month is does not exist for this month and year, None is returned.
    This can happen for many fifth week days.
    """
    day_of_week, week_of_month = day_of_month.day_of_week, day_of_month.week_of_month
    first = date(year=year, month=month, day=1)
    day = (day_of_week - first.isoweekday()) % 7 + 1 + (week_of_month - 1) * 7
    try:
        return date(year=year, month=month, day=day)
    except ValueError:
        return None  # this day_of_month is N/A (some fifth days)


def day_of_month_to_text(day_of_month):
    """
    Convert a DayOfMonth object to human-readable text.
    """
    week = weeks_of_month[day_of_month.week_of_month]
    day = days_of_week[day_of_month.day_of_week]
    return f"{week} {day}"


def is_friday(date):
    return date.isoweekday() == 5


def is_weekend(date):
    return date.isoweekday() in {6, 7}


def split_recurrence(recurrence):
    """
    https://github.com/django-recurrence/django-recurrence/blob/master/recurrence/base.py
    """
    if isinstance(recurrence, str):
        recurrence = deserialize(recurrence)

    def is_excluded(day_of_month):
        for rule in recurrence.exrules:
            for day in rule.byday:
                if rule.freq == WEEKLY:
                    if day.number + 1 == day_of_month.day_of_week:
                        return True
                elif rule.freq == MONTHLY:
                    if (
                        day.number + 1 == day_of_month.day_of_week
                        and day.index == day_of_month.week_of_month
                    ):
                        return True
        return False

    def last_to_fifth(index):
        if index == -1:
            return 5
        return index

    for rule in recurrence.rrules:
        for day in rule.byday:
            if rule.freq == MONTHLY:
                day_in_month = DayOfMonth(
                    day.number + 1, last_to_fifth(day.index))
                if not is_excluded(day_in_month):
                    yield day_in_month
            elif rule.freq == WEEKLY:
                for i in range(1, 6):
                    day_in_month = DayOfMonth(day.number + 1, i)
                    if not is_excluded(day_in_month):
                        yield day_in_month
