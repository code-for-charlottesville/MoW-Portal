import logging
from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import BooleanField, DateField, F, Value
from django.test import TestCase
from freezegun import freeze_time
from recurrence import serialize

from interfaces.recurrence import (
    FR,
    MO,
    WE,
    WEEKLY,
    Recurrence,
    Rule,
    date_to_day_of_month,
    one_day_recurrence,
)
from models.models import (
    Actual,
    Assignment,
    Customer,
    CustomerRecord,
    DateRange,
    Job,
    JobType,
    Payment,
    Route,
    Substitution,
    Volunteer,
    VolunteerRecord,
    actual_dict_to_namedtuple,
)

log = logging.getLogger(__name__)


@patch("interfaces.address_lookup.validate",
       lambda *a, **k: {"lat": None, "lng": None})
class TestCustomer(TestCase):
    def test_num_meals_on_day(self):

        payment = Payment.objects.create(name="testpayment")
        job_type = JobType.objects.create(name="test_type")
        route = Route.objects.create(
            description="testroute desc", number="1", job_type=job_type
        )

        customer = Customer.objects.create(
            route=route,
            join_date="1999-12-11",
            pays=payment,
            active=True,
            first_name="test",
            last_name="customer",
            address="555 Main St.",
            phone="5555555555",
            printed_notes="no notes",
            birth_date="1997-12-12",
            sex="M",
            contact="5555555555",
            contact_phone="5555555555",
            diet=None,
            cold_diet_restrictions="no",
            hot_diet_restrictions="no",
            pet=None,
            petfood=None,
            end_date="2019-04-04",
            end_reason="none",
            referred="no",
            ref_phone="5555555555",
            bill_to="nobody",
            notes="no notes",
            lat=38.037740,
            lon=-78.487490,
            num_weekend_meals=2,
            meal_recurrence=serialize(
                Recurrence(rrules=[Rule(freq=WEEKLY, byday=(MO, WE, FR))])
            ),
        )
        DateRange.objects.create(
            customer=customer,
            start_date=date(year=2050, month=1, day=1),
            end_date=date(year=2050, month=1, day=9),
        )
        self.assertFalse(
            customer.num_meals_on_day(
                date(
                    year=2050,
                    month=1,
                    day=9)))
        self.assertTrue(
            customer.num_meals_on_day(
                date(
                    year=2050,
                    month=1,
                    day=10)))
        self.assertFalse(
            customer.num_meals_on_day(
                date(
                    year=2050,
                    month=1,
                    day=11)))
        self.assertTrue(
            customer.num_meals_on_day(
                date(
                    year=2050,
                    month=1,
                    day=12)))
        self.assertFalse(
            customer.num_meals_on_day(
                date(
                    year=2050,
                    month=1,
                    day=13)))
        self.assertTrue(
            customer.num_meals_on_day(
                date(
                    year=2050,
                    month=1,
                    day=14)))
        self.assertFalse(
            customer.num_meals_on_day(
                date(
                    year=2050,
                    month=1,
                    day=5)))

    def test_num_meals_on_day_historical(self):

        payment = Payment.objects.create(name="testpayment")
        job_type = JobType.objects.create(name="test_type")
        route = Route.objects.create(
            description="testroute desc", number="1", job_type=job_type
        )

        customer = Customer.objects.create(
            route=route,
            join_date="1999-12-11",
            pays=payment,
            active=True,
            first_name="test",
            last_name="customer",
            address="555 Main St.",
            phone="5555555555",
            printed_notes="no notes",
            birth_date="1997-12-12",
            sex="M",
            contact="5555555555",
            contact_phone="5555555555",
            diet=None,
            cold_diet_restrictions="no",
            hot_diet_restrictions="no",
            pet=None,
            petfood=None,
            end_date="2019-04-04",
            end_reason="none",
            referred="no",
            ref_phone="5555555555",
            bill_to="nobody",
            notes="no notes",
            num_weekend_meals=2,
            meal_recurrence=serialize(
                Recurrence(rrules=[Rule(freq=WEEKLY, byday=(MO, WE, FR))])
            ),
        )
        CustomerRecord.objects.create(
            customer=customer, date=date(
                year=2020, month=1, day=1), num_meals=100, )
        CustomerRecord.objects.create(
            customer=customer, date=date(
                year=2020, month=1, day=2), num_meals=101, )
        self.assertEqual(
            customer.num_meals_on_day(
                date(
                    year=2020,
                    month=1,
                    day=1)),
            100)
        self.assertEqual(
            customer.num_meals_on_day(
                date(
                    year=2020,
                    month=1,
                    day=2)),
            101)
        self.assertEqual(
            customer.num_meals_on_day(
                date(
                    year=2020,
                    month=1,
                    day=3)),
            0)


class TestJobVolunteerAssignment(TestCase):
    def setUp(self):
        User.objects.create(username="user")
        self.user = User.objects.get(username="user")
        self.vol = Volunteer.objects.get(user=self.user)
        job_type = JobType.objects.create(name="test_type")
        self.job = Job.objects.create(name="TestJob", job_type=job_type)

    def test_recurring_uniqueness(self):
        """Test that the job, volunteer, and day_of_month fields are unique together
        for Assignments"""

        # first and third mondays of the month

        Assignment.objects.create(
            job=self.job, volunteer=self.vol, day_of_week=1, week_of_month=1,
        )
        with self.assertRaises(IntegrityError):
            Assignment.objects.create(
                job=self.job,
                volunteer=self.vol,
                day_of_week=1,
                week_of_month=1,
            )

    def test_recurring_uniqueness_excludes_nulls(self):
        """Test that duplicate recurring assignments are allowed if the volunteer is null,
        indicating an "OPEN ROUTE", of which there can be many for packing jobs."""

        # first and third mondays of the month
        day_of_month = one_day_recurrence(MO, 2)

        Assignment.objects.create(
            job=self.job, volunteer=None, day_of_week=1, week_of_month=1,
        )
        Assignment.objects.create(
            job=self.job, volunteer=None, day_of_week=1, week_of_month=1,
        )

    def test_substitution_uniqueness(self):
        """Test that the job, volunteer, and date fields are unique together
        for Substitutions"""

        sub_date = date(year=2, month=2, day=2)
        assignment = Assignment.objects.create(
            job=self.job, volunteer=None, day_of_week=1, week_of_month=1,
        )
        Substitution.objects.create(
            assignment=assignment,
            volunteer=self.vol,
            date=sub_date)
        with self.assertRaises(IntegrityError):
            Substitution.objects.create(
                assignment=assignment, volunteer=self.vol, date=sub_date
            )

    def test_substitution_uniqueness_excludes_null(self):
        """Test that duplicate substitutions are allowed if the volunteer is null,
        indicating a to-be-filled substitution, of which there can be many."""
        sub_date = date(year=2, month=2, day=2)
        assignment = Assignment.objects.create(
            job=self.job, volunteer=None, day_of_week=1, week_of_month=1,
        )
        Substitution.objects.create(
            assignment=assignment,
            volunteer=None,
            date=sub_date)
        Substitution.objects.create(
            assignment=assignment,
            volunteer=None,
            date=sub_date)


class TestCustomMonthlies(TestCase):
    def setUp(self):
        User.objects.create(
            username="user",
            first_name="first",
            last_name="last")
        self.user = User.objects.get(username="user")
        self.vol = Volunteer.objects.get(user=self.user)
        job_type = JobType.objects.create(name="test_type")
        Job.objects.create(name="TestJob", job_type=job_type)
        self.job = Job.objects.get(name="TestJob")
        self.assignment = Assignment.objects.create(
            job=self.job, volunteer=self.vol, day_of_week=1, week_of_month=1
        )

    def test_assignment_str(self):
        expected = "first last is volunteering for TestJob on the First Monday"
        str_value = str(self.assignment)
        self.assertEqual(str_value, expected)

    def test_assignment_day_of_month_str(self):
        day_of_month_str = self.assignment.get_day_of_month_str()
        expected = "First Monday"
        self.assertEqual(day_of_month_str, expected)


class TestCustomerRoutes(TestCase):
    @patch("interfaces.address_lookup.validate",
           lambda *a, **k: {"lat": None, "lng": None})
    def setUp(self):
        job_type = JobType.objects.create(name="test_type")
        Route.objects.create(number=1, name="Route 1", job_type=job_type)
        self.route = Route.objects.get(number=1)
        self.customers = []
        for i in range(1, 4):
            name = f"customer{i}"
            Customer.objects.create(
                first_name=name, route=self.route, address="")
            self.customers.append(Customer.objects.get(first_name=name))

    def test_customer_order_with_respect_to_route(self):
        self.assertEqual(
            list(
                self.route.get_customer_order()), [
                c.pk for c in self.customers])
        self.route.set_customer_order([c.pk for c in reversed(self.customers)])
        self.assertEqual(list(self.route.get_customer_order()), [
            c.pk for c in reversed(self.customers)], )
        self.assertEqual(
            self.customers[1].get_next_in_order(),
            self.customers[0])
        self.assertEqual(
            self.customers[1].get_previous_in_order(),
            self.customers[2])


@freeze_time("2020-3-2")
class TestActuals(TestCase):
    """
    This class is just for testing the Assignment.actuals() functions, which is
    quite complex.

    The general approach is to split the actuals by cases. The cases are that:
     - actual is on today or in the future, and...
        - the actual volunteer and the original are different
            - this indicates a subsitution
        - the actual volunteer and the orignal are the same
            - this indicates an unsubstituted assignment
     - actual is in the past (not including today)
         - this indicates a VolunteerRecord

    By asserting that the actuals is a subset of the directly queried data
    and that the directly queried data is a subset of the actuals for each case,
    we prove that the set of actuals is equivalent to directly querying the data for
    each case and therefor always.
    """

    __author__ = "Maxwell Patek"

    def setUp(self):
        """
        Here we set up a signifigant amount of data, spanning many days
        many days_of_month, many num_vols_required, many volunteers, many jobs,
        including unsubstituted assignments, substitutions, and historical data
        that conflicts with current data.
        """
        today = date.today()
        self.assertEqual(today, date(year=2020, month=3, day=2))
        job_types = ["3", "2", "4", "1"] * 3
        self.jobs = [
            Route.objects.create(
                name=f"Job{i}",
                num_vols_required=i,
                number=20 - i,
                job_type=JobType.objects.get_or_create(name=f"Type{job_types[i]}")[0],
            )
            for i in range(1, 11)
        ]
        self.usrs = [
            User.objects.create(
                username=f"user{i}",
                first_name=f"First{i}",
                last_name=f"Last{i}",
            ) for i in range(
                1,
                11)]
        self.vols = [self.usrs[i].volunteer for i in range(10)] + [None, None]
        vol_index = 0
        self.assignments = []
        for job in self.jobs:
            for week_of_month in range(1, 6):
                for day_of_week in range(1, 6):
                    self.assignments.append(
                        Assignment.objects.create(
                            volunteer=self.vols[vol_index % len(self.vols)],
                            job=job,
                            day_of_week=day_of_week,
                            week_of_month=week_of_month,
                        )
                    )
                    vol_index += 1

        self.subs = []
        day = today - timedelta(days=30)
        while day < today + timedelta(days=30):
            dom = date_to_day_of_month(day)
            asses = [
                a
                for a in self.assignments
                if (a.day_of_week == dom.day_of_week and a.week_of_month == dom.week_of_month)
            ]
            if not asses:
                day += timedelta(days=2)
                continue
            for i in range(len(asses) % 2, len(asses), 2):
                ass = asses[i]
                self.subs.append(
                    Substitution.objects.create(
                        volunteer=self.vols[
                            (self.vols.index(ass.volunteer) + 1) % len(self.vols)
                        ],
                        assignment=ass,
                        date=day,
                    )
                )
            day += timedelta(days=2)

        self.records = []
        day = today - timedelta(days=29)
        while day <= today + timedelta(days=2):
            dom = date_to_day_of_month(day)
            asses = [
                a
                for a in self.assignments
                if (a.day_of_week == dom.day_of_week and a.week_of_month == dom.week_of_month)
            ]
            if not asses:
                day += timedelta(days=2)
                continue
            for i in range(len(asses) % 2, len(asses), 2):
                ass = asses[i]
                self.records.append(
                    VolunteerRecord.objects.create(
                        volunteer=self.vols[
                            (self.vols.index(ass.volunteer) + 1) % len(self.vols)
                        ],
                        job=ass.job,
                        date=day,
                        original=ass.volunteer,
                        is_substitution=True,
                    )
                )
            day += timedelta(days=2)

    def test_subs_are_legit(self):
        """
        Test that all actuals where volunteer is not original are actual substitutions.
        """
        actuals = Assignment.actuals(
            date.today(),
            date.today() +
            timedelta(
                days=30))
        for actual in actuals:
            if actual.is_substitution:
                Substitution.objects.get(
                    volunteer=actual.volunteer,
                    assignment__volunteer=actual.original,
                    assignment__job=actual.job,
                    date=actual.date,
                )

    def test_all_subs_included(self):
        """
        Test that all substitutions are in the actuals.
        """
        today = date.today()
        actuals = set(Assignment.actuals(today, today + timedelta(days=30)))
        subs = Substitution.objects.filter(
            date__gte=today, date__lte=today + timedelta(days=30)
        )
        for sub in subs:
            actual = Actual(
                volunteer=sub.volunteer,
                job=sub.assignment.job,
                original=sub.assignment.volunteer,
                date=sub.date,
                is_substitution=True,
            )
            self.assertIn(actual, actuals)

    def test_assignments_are_legit(self):
        """
        Test that all actuals where volunteer is original are actual unsubstituted assignments.
        """
        actuals = Assignment.actuals(
            date.today(),
            date.today() +
            timedelta(
                days=30))
        for actual in actuals:
            if not actual.is_substitution:
                dom = date_to_day_of_month(actual.date)
                assignment = Assignment.objects.get(
                    volunteer=actual.volunteer,
                    job=actual.job,
                    day_of_week=dom.day_of_week,
                    week_of_month=dom.week_of_month,
                )
                self.assertFalse(
                    Substitution.objects.filter(
                        assignment=assignment,
                        date=actual.date))

    def test_all_assignments_included(self):
        """
        Test all unsubstituted assignments are in the actuals.
        """
        today = date.today()
        actuals = set(Assignment.actuals(today, today + timedelta(days=30)))
        day = today
        while day < today + timedelta(days=30):
            dom = date_to_day_of_month(day)
            asses = list(
                Assignment.objects.filter(
                    day_of_week=dom.day_of_week,
                    week_of_month=dom.week_of_month,
                ))
            if not asses:
                day += timedelta(days=1)
                continue

            for ass in asses:
                try:
                    Substitution.objects.get(assignment=ass, date=day)
                    continue
                except Substitution.DoesNotExist:
                    pass
                actual = Actual(
                    volunteer=ass.volunteer,
                    job=ass.job,
                    original=ass.volunteer,
                    date=day,
                    is_substitution=False,
                )
                self.assertIn(actual, actuals)
            day += timedelta(days=1)

    def test_records_are_legit(self):
        """
        Test that all actuals from the past are actual VolunteerRecords.
        """
        today = date.today()
        actuals = Assignment.actuals(today - timedelta(days=30), today)
        for actual in actuals:
            VolunteerRecord.objects.get(
                volunteer=actual.volunteer,
                original=actual.original,
                job=actual.job,
                date=actual.date,
            )

    def test_all_records_included(self):
        """
        Test that all VolunteerRecords are in the actuals.
        """
        today = date.today()
        actuals = set(
            Assignment.actuals(
                date.today() -
                timedelta(
                    days=30),
                today))
        records = VolunteerRecord.objects.filter(
            date__gte=date.today() - timedelta(days=30), date__lt=today
        )
        for record in records:
            actual = Actual(
                volunteer=record.volunteer,
                job=record.job,
                original=record.original,
                date=record.date,
                is_substitution=record.is_substitution,
            )
            self.assertIn(actual, actuals)

    def test_no_duplicate(self):
        """
        Test that there are no duplicates in the actuals.
        """
        today = date.today()
        actuals_list = list(
            Assignment.actuals(
                today,
                today +
                timedelta(
                    days=30)))
        actuals_set = set(
            Assignment.actuals(
                today,
                today +
                timedelta(
                    days=30)))
        self.assertEqual(len(actuals_list), len(actuals_set))

    def test_filters(self):
        """
        test filtering an actuals query on volunteer, original, and job
        """
        today = date.today()
        days30 = timedelta(days=30)
        for vol, orig in zip(self.vols[1:] + [self.vols[0]], self.vols):
            for job in self.jobs:
                actuals = set(
                    filter(
                        lambda a: a.is_substitution,
                        Assignment.actuals(
                            today - days30,
                            today + days30,
                            volunteer=vol,
                            original=orig,
                            job=job,
                        ),
                    )
                )
                subs = set(
                    map(
                        actual_dict_to_namedtuple,
                        Substitution.objects.filter(
                            date__gte=today,
                            date__lt=today + days30,
                            volunteer=vol,
                            assignment__job=job,
                            assignment__volunteer=orig,
                        ).values(
                            actual_volunteer=F("volunteer"),
                            actual_job=F("assignment__job"),
                            actual_date=F("date"),
                            actual_original=F("assignment__volunteer"),
                            actual_is_substitution=Value(True, BooleanField()),
                        ),
                    )
                ) | set(
                    map(
                        actual_dict_to_namedtuple,
                        VolunteerRecord.objects.filter(
                            date__gte=today - days30,
                            date__lt=today,
                            volunteer=vol,
                            job=job,
                            original=orig,
                        ).values(
                            actual_volunteer=F("volunteer"),
                            actual_job=F("job"),
                            actual_date=F("date"),
                            actual_original=F("original"),
                            actual_is_substitution=F("is_substitution"),
                        ),
                    )
                )

                self.assertEqual(actuals, subs)

    def test_deleted_vol(self):
        """
        Test that deleting a volunteer doesn't mess up record queries.
        """
        today = date.today()
        days30 = timedelta(days=30)
        deleted_vols = [self.vols[4], self.vols[5]]
        for vol in deleted_vols:
            vol.delete()
            self.vols[self.vols.index(vol)] = None

        for vol, orig in zip(self.vols[1:] + [self.vols[0]], self.vols):
            actuals = set(
                Assignment.actuals(
                    today - days30,
                    today + days30,
                    volunteer=vol,
                    original=orig,
                ))
            subs = set(map(actual_dict_to_namedtuple,
                           Substitution.objects.filter(date__gte=today,
                                                       date__lt=today + days30,
                                                       volunteer=vol,
                                                       assignment__volunteer=orig,
                                                       ).values(actual_volunteer=F("volunteer"),
                                                                actual_job=F("assignment__job"),
                                                                actual_date=F("date"),
                                                                actual_original=F("assignment__volunteer"),
                                                                actual_is_substitution=Value(True,
                                                                                             BooleanField()),
                                                                ),
                           )) | set(map(actual_dict_to_namedtuple,
                                        VolunteerRecord.objects.filter(date__gte=today - days30,
                                                                       date__lt=today,
                                                                       volunteer=vol,
                                                                       original=orig,
                                                                       ).values(actual_volunteer=F("volunteer"),
                                                                                actual_job=F("job"),
                                                                                actual_date=F("date"),
                                                                                actual_original=F("original"),
                                                                                actual_is_substitution=F("is_substitution"),
                                                                                ),
                                        ))
            if vol is orig is None:
                day = today
                while day < today + days30:
                    dom = date_to_day_of_month(day)
                    subs |= set(
                        filter(
                            lambda a: not Substitution.objects.filter(
                                volunteer=a.volunteer,
                                assignment__job=a.job,
                                assignment__volunteer=a.original,
                                date=day,
                            ).exists(),
                            map(
                                actual_dict_to_namedtuple,
                                Assignment.objects.filter(
                                    day_of_week=dom.day_of_week,
                                    week_of_month=dom.week_of_month,
                                    volunteer=orig,
                                ).values(
                                    actual_volunteer=F("volunteer"),
                                    actual_job=F("job"),
                                    actual_date=Value(day, output_field=DateField()),
                                    actual_original=F("volunteer"),
                                    actual_is_substitution=Value(False, BooleanField()),
                                ),
                            ),
                        )
                    )
                    day += timedelta(days=1)

            self.assertEqual(actuals, subs)

    def test_order_by(self):
        """
        Test that ordering actuals works.
        """

        def assertSorted(l, *, key):
            self.assertTrue(all(key(l[i]) <= key(l[i + 1])
                                for i in range(len(l) - 1)))

        today = date.today()
        days30 = timedelta(days=30)
        actuals = list(
            Assignment.actuals(
                today - days30,
                today + days30,
                order_by="date"))
        assertSorted(actuals, key=lambda a: a.date)
        actuals = list(
            Assignment.actuals(
                today - days30,
                today + days30,
                order_by="volunteer"))
        assertSorted(
            actuals,
            key=lambda a: (
                a.volunteer.user.last_name if a.volunteer else "zzzzz",
                a.volunteer.user.first_name if a.volunteer else "zzzzz",
            ),
        )
        actuals = list(
            Assignment.actuals(
                today - days30,
                today + days30,
                order_by="job"))
        assertSorted(
            actuals,
            key=lambda a: (
                a.job.get_route_number(),
                a.job.job_type.strip_space_in_name))

    def test_exclude_unfilled(self):
        today = date.today()
        days30 = timedelta(days=30)

        unexcluded_actuals = set(
            Assignment.actuals(
                today - days30,
                today + days30))
        excluded_actuals = set(
            Assignment.actuals(
                today - days30,
                today + days30,
                exclude_unfilled=True))
        exclusions = unexcluded_actuals - excluded_actuals

        for actual in exclusions:
            self.assertFalse(actual.volunteer)
            self.assertFalse(actual.date < today)
        for actual in excluded_actuals:
            if actual.date >= today:
                self.assertTrue(actual.volunteer)
