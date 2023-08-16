from datetime import date
from itertools import product

from django.test import TestCase

from interfaces.recurrence import (
    DayOfMonth,
    date_to_day_of_month,
    day_of_month_to_date,
    split_recurrence,
)


class TestRecurrenceInterface(TestCase):
    __author__ = "Maxwell Patek"

    def test_day_of_month_to_date_friday_first(self):
        friday_first = dict(year=2019, month=11)
        first = DayOfMonth(day_of_week=5, week_of_month=1)
        expected_first = date(**friday_first, day=1)
        self.assertEqual(
            day_of_month_to_date(
                **friday_first,
                day_of_month=first),
            expected_first)

        fourth = DayOfMonth(day_of_week=1, week_of_month=1)
        expected_fourth = date(**friday_first, day=4)
        self.assertEqual(
            day_of_month_to_date(
                **friday_first,
                day_of_month=fourth),
            expected_fourth)

        fifth_fri = DayOfMonth(day_of_week=5, week_of_month=5)
        expected_fifth_fri = date(**friday_first, day=29)
        self.assertEqual(
            day_of_month_to_date(
                **friday_first,
                day_of_month=fifth_fri),
            expected_fifth_fri,
        )

    def test_day_of_month_to_date_monday_first(self):
        monday_first = dict(year=2019, month=7)
        first = DayOfMonth(day_of_week=1, week_of_month=1)
        expected_first = date(**monday_first, day=1)
        self.assertEqual(
            day_of_month_to_date(
                **monday_first,
                day_of_month=first),
            expected_first)

        fifth = DayOfMonth(day_of_week=5, week_of_month=1)
        expected_fifth = date(**monday_first, day=5)
        self.assertEqual(
            day_of_month_to_date(
                **monday_first,
                day_of_month=fifth),
            expected_fifth)

        fifth_wed = DayOfMonth(day_of_week=3, week_of_month=5)
        expected_fifth_wed = date(**monday_first, day=31)
        self.assertEqual(
            day_of_month_to_date(
                **monday_first,
                day_of_month=fifth_wed),
            expected_fifth_wed,
        )

    def test_day_of_month_to_date_does_not_exist(self):
        day_of_month = DayOfMonth(1, 5)
        year = 2019
        month = 11
        self.assertIsNone(day_of_month_to_date(day_of_month, month, year))

    def test_date_to_day_of_month_friday_first(self):
        friday_first = dict(year=2019, month=11)
        expected_first = DayOfMonth(day_of_week=5, week_of_month=1)
        first = date(**friday_first, day=1)
        self.assertEqual(date_to_day_of_month(first), expected_first)

        expected_fourth = DayOfMonth(day_of_week=1, week_of_month=1)
        fourth = date(**friday_first, day=4)
        self.assertEqual(date_to_day_of_month(fourth), expected_fourth)

        expected_fifth_fri = DayOfMonth(day_of_week=5, week_of_month=5)
        fifth_fri = date(**friday_first, day=29)
        self.assertEqual(date_to_day_of_month(fifth_fri), expected_fifth_fri)

    def test_date_to_day_of_month_monday_first(self):
        monday_first = dict(year=2019, month=7)
        expected_first = DayOfMonth(day_of_week=1, week_of_month=1)
        first = date(**monday_first, day=1)
        self.assertEqual(date_to_day_of_month(first), expected_first)

        expected_fifth = DayOfMonth(day_of_week=5, week_of_month=1)
        fifth = date(**monday_first, day=5)
        self.assertEqual(date_to_day_of_month(fifth), expected_fifth)

        expected_fifth_wed = DayOfMonth(day_of_week=3, week_of_month=5)
        fifth_wed = date(**monday_first, day=31)
        self.assertEqual(date_to_day_of_month(fifth_wed), expected_fifth_wed)

    def test_date_day_of_month_inverses(self):
        """
        Test that date_to_day_of_month and day_of_month_to_date are inverses for the next
        decade.
        """
        for year, month in zip(range(2020, 2031), range(1, 13)):
            for week, day in product(range(1, 6), range(1, 8)):
                day_of_month = DayOfMonth(day_of_week=day, week_of_month=week)
                the_date = day_of_month_to_date(day_of_month, month, year)
                if not the_date:
                    break
                new_day_of_month = date_to_day_of_month(the_date)
                self.assertEqual(day_of_month, new_day_of_month)
        for year, month, day in zip(
            range(
                2020, 2031), range(
                1, 13), range(
                1, 32)):
            try:
                the_date = date(year=year, month=month, day=day)
            except ValueError:
                break
            day_of_month = date_to_day_of_month(the_date)
            new_date = day_of_month_to_date(day_of_month, month, year)
            self.assertEqual(
                the_date,
                new_date,
                (f"year={year}, month={month}, day={day}, day_of_week={day_of_month},"
                 " new_date={new_date}"),
            )

    def test_split_recurrence_single_weekly_rule(self):
        rule_str = "RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR"
        actual = set(split_recurrence(rule_str))
        expected = {DayOfMonth(day, week)
                    for day, week in product([1, 3, 5], range(1, 6))}
        self.assertEqual(actual, expected)

    def test_split_recurrence_single_monthly_rule(self):
        rule_str = "RRULE:FREQ=MONTHLY;BYDAY=4TU"
        actual = set(split_recurrence(rule_str))
        expected = {DayOfMonth(2, 4)}
        self.assertEqual(actual, expected)

    def test_split_recurrence_mixed_rules(self):
        rule_str = """RRULE:FREQ=MONTHLY;BYDAY=4TU
RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR"""
        actual = set(split_recurrence(rule_str))
        expected = {DayOfMonth(2, 4)} | {DayOfMonth(day, week)
                                         for day, week in product([1, 3, 5], range(1, 6))}
        self.assertEqual(actual, expected)

    def test_split_recurrence_weekly_xrule(self):
        rule_str = "EXRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR"
        actual = set(split_recurrence(rule_str))
        self.assertFalse(actual)

        rule_str = """RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR
EXRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"""
        actual = set(split_recurrence(rule_str))
        self.assertFalse(actual)

    def test_split_recurrence_monthly_xrule(self):
        rule_str = """RRULE:FREQ=MONTHLY;BYDAY=4TU,4TH
EXRULE:FREQ=MONTHLY;BYDAY=4TU"""
        actual = set(split_recurrence(rule_str))
        expected = {DayOfMonth(4, 4)}
        self.assertEqual(actual, expected)

    def test_split_recurrence_mixed_rules_xrules(self):
        rule_str = """RRULE:FREQ=MONTHLY;BYDAY=4TU,4TH
RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR
EXRULE:FREQ=WEEKLY;BYDAY=TU
EXRULE:FREQ=MONTHLY;BYDAY=3MO"""
        actual = set(split_recurrence(rule_str))
        expected = {DayOfMonth(4, 4)} | {
            DayOfMonth(day, week) for day, week in product([1, 3, 5], range(1, 6))
        } - {DayOfMonth(1, 3)}
        self.assertEqual(actual, expected)

    def test_split_recurrence_fifth_week(self):
        rule_str = """RRULE:FREQ=MONTHLY;BYDAY=-1FR
EXRULE:FREQ=MONTHLY;BYDAY=4FR"""
        actual = set(split_recurrence(rule_str))
        expected = {DayOfMonth(5, 5)}
        self.assertEqual(actual, expected)

        rule_str = """RRULE:FREQ=MONTHLY;BYDAY=-1FR
EXRULE:FREQ=MONTHLY;BYDAY=4FR"""
        actual = set(split_recurrence(rule_str))
        self.assertEqual(actual, expected)
