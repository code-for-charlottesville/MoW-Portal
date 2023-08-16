import datetime
from unittest import SkipTest

# https://docs.python.org/3/library/unittest.mock.html
from unittest.mock import patch

from django.contrib.auth.models import User
from django.http import FileResponse
from django.test import Client, TestCase
from django.urls import reverse
from freezegun import freeze_time
from recurrence import serialize

from interfaces.recurrence import FR, MO, TH, TU, WE, WEEKLY, Recurrence, Rule
from meals.constants import RETENTION
from models.models import (
    Actual,
    Assignment,
    Customer,
    CustomerRecord,
    DateRange,
    Job,
    JobType,
    ManagerAnnouncement,
    Payment,
    Route,
    Substitution,
    User,
    Volunteer,
    VolunteerRecord,
)


class TestCronCustomerRecord(TestCase):
    __author__ = "Kevin Naddoni & Max Patek"

    @patch("interfaces.address_lookup.validate",
           lambda *a, **k: {"lat": None, "lng": None})
    def setUp(self):
        # set up customer, payment, route,
        self.client = Client()
        self.client.force_login(
            User.objects.get_or_create(
                username="admin",
                password="pass@123",
                email="admin@admin.com",
                is_staff=True,
            )[0])

        self.payment = Payment.objects.create(name="testpayment")
        job_type = JobType.objects.create(name="test_type")
        self.route = Route.objects.create(
            description="testroute desc", number="1", job_type=job_type
        )

        self.customer = Customer.objects.create(
            route=self.route,
            join_date="1999-12-11",
            pays=self.payment,
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
            num_weekend_meals="2",
            meal_recurrence=serialize(
                Recurrence(Rule(freq=WEEKLY, byday=(MO, TU, WE, TH, FR)))
            ),
        )

    @freeze_time("2020-1-8")
    @patch("pdfs.cron.Customer.num_meals_on_day")
    def test_week_day(self, mocked_num_meals_on_day):
        mocked_num_meals_on_day.return_value = 1
        response = self.client.get(reverse("cron_daily"))
        self.assertEqual(response.status_code, 200)
        CustomerRecord.objects.get(
            customer=self.customer,
            date=datetime.date(year=2020, month=1, day=8),
            num_meals=1,
            payment_type=self.payment,
            route_assigned=self.route,
        )

    @freeze_time("2020-1-8")
    @patch("pdfs.cron.Customer.num_meals_on_day")
    def test_week_day_doesnt_receive(self, mocked_num_meals_on_day):
        mocked_num_meals_on_day.return_value = 0
        response = self.client.get(reverse("cron_daily"))
        self.assertEqual(response.status_code, 200)
        with self.assertRaises(CustomerRecord.DoesNotExist):
            CustomerRecord.objects.get(
                customer=self.customer,
                date=datetime.date(year=2020, month=1, day=8),
                payment_type=self.payment,
                route_assigned=self.route,
            )

    @freeze_time("2020-1-10")
    @patch("pdfs.cron.Customer.num_meals_on_day")
    def test_friday(self, mocked_num_meals_on_day):
        mocked_num_meals_on_day.return_value = 3
        response = self.client.get(reverse("cron_daily"))
        self.assertEqual(response.status_code, 200)
        CustomerRecord.objects.get(
            customer=self.customer,
            date=datetime.date(year=2020, month=1, day=10),
            num_meals=3,
            payment_type=self.payment,
            route_assigned=self.route,
        )

    @freeze_time("2020-1-11")
    @patch("pdfs.cron.Customer.num_meals_on_day")
    def test_weekend(self, mocked_num_meals_on_day):
        raise SkipTest  # TODO move to test_num_meals_on_day in models project

        mocked_num_meals_on_day.return_value = True
        response = self.client.get(reverse("cron_daily"))
        self.assertEqual(response.status_code, 200)
        with self.assertRaises(CustomerRecord.DoesNotExist):
            CustomerRecord.objects.get(
                customer=self.customer,
                date=datetime.date(year=2020, month=1, day=11),
                num_meals=3,
                payment_type=self.payment,
                route_assigned=self.route,
            )

    @freeze_time("2020-1-8")
    @patch("pdfs.cron.Customer.num_meals_on_day")
    def test_successive_no_change(self, mocked_num_meals_on_day):
        mocked_num_meals_on_day.return_value = 1
        response = self.client.get(reverse("cron_daily"))
        self.assertEqual(response.status_code, 200)
        CustomerRecord.objects.get(
            customer=self.customer,
            date=datetime.date(year=2020, month=1, day=8),
            num_meals=1,
            payment_type=self.payment,
            route_assigned=self.route,
        )
        response = self.client.get(reverse("cron_daily"))
        self.assertEqual(response.status_code, 200)
        CustomerRecord.objects.get(
            customer=self.customer,
            date=datetime.date(year=2020, month=1, day=8),
            num_meals=1,
            payment_type=self.payment,
            route_assigned=self.route,
        )

    @freeze_time("2020-1-8")
    @patch("pdfs.cron.Customer.num_meals_on_day")
    @patch("interfaces.address_lookup.validate",
           lambda *a, **k: {"lat": None, "lng": None})
    def test_successive_with_change(self, mocked_num_meals_on_day):
        mocked_num_meals_on_day.return_value = 1
        response = self.client.get(reverse("cron_daily"))
        self.assertEqual(response.status_code, 200)
        CustomerRecord.objects.get(
            customer=self.customer,
            date=datetime.date(year=2020, month=1, day=8),
            num_meals=1,
            payment_type=self.payment,
            route_assigned=self.route,
        )
        new_payment = Payment.objects.create(name="newpayment")
        self.customer.pays = new_payment
        self.customer.save()
        response = self.client.get(reverse("cron_daily"))
        self.assertEqual(response.status_code, 200)
        CustomerRecord.objects.get(
            customer=self.customer,
            date=datetime.date(year=2020, month=1, day=8),
            num_meals=1,
            payment_type=new_payment,
            route_assigned=self.route,
        )
        with self.assertRaises(CustomerRecord.DoesNotExist):
            CustomerRecord.objects.get(
                customer=self.customer,
                date=datetime.date(year=2020, month=1, day=8),
                num_meals=1,
                payment_type=self.payment,
                route_assigned=self.route,
            )


@freeze_time("2020-03-18")
@patch("models.models.Assignment.actuals")
class TestCronVolunteerRecord(TestCase):
    __author__ = "Max Patek"

    def setUp(self):
        self.usrs = [
            User.objects.create(
                username=f"user{i}") for i in range(10)]
        self.vols = [
            Volunteer.objects.get(
                user__username=f"user{i}") for i in range(10)]
        self.jobs = [
            Job.objects.create(
                name=f"job{i}", job_type=JobType.objects.get_or_create(name="TestType")[0],
            )
            for i in range(10)
        ]
        self.yesterdays_records = [
            VolunteerRecord.objects.create(
                volunteer=self.vols[0],
                job=self.jobs[0],
                date=datetime.date.today() - datetime.timedelta(days=1),
                original=self.vols[1],
                is_substitution=True,
            )
        ]

    def test_weekday_one_assignment(self, mocked_actuals):
        today = datetime.date.today()
        mocked_actuals.return_value = (
            Actual(
                volunteer=self.vols[0],
                job=self.jobs[0],
                date=today,
                original=self.vols[0],
                is_substitution=False,
            ),
        )
        response = self.client.get(reverse("cron_daily"))
        record = VolunteerRecord.objects.get(
            volunteer=self.vols[0],
            job=self.jobs[0],
            date=today,
            original=self.vols[0],
            is_substitution=False,
        )
        all_today = set(VolunteerRecord.objects.filter(date=today))
        self.assertEqual({record}, all_today)

    def test_weekday_mixed(self, mocked_actuals):
        today = datetime.date.today()
        mocked_actuals.return_value = (
            Actual(
                volunteer=self.vols[0],
                job=self.jobs[0],
                date=today,
                original=self.vols[0],
                is_substitution=False,
            ),
            Actual(
                volunteer=self.vols[1],
                job=self.jobs[1],
                date=today,
                original=self.vols[2],
                is_substitution=True,
            ),
            Actual(
                volunteer=None,
                job=self.jobs[1],
                date=today,
                original=None,
                is_substitution=True,
            ),
        )
        response = self.client.get(reverse("cron_daily"))
        records = {
            VolunteerRecord.objects.get(
                volunteer=self.vols[0],
                job=self.jobs[0],
                date=today,
                original=self.vols[0],
                is_substitution=False,
            ),
            VolunteerRecord.objects.get(
                volunteer=self.vols[1],
                job=self.jobs[1],
                date=today,
                original=self.vols[2],
                is_substitution=True,
            ),
            VolunteerRecord.objects.get(
                volunteer=None,
                job=self.jobs[1],
                date=today,
                original=None,
                is_substitution=True,
            ),
        }
        all_today = set(VolunteerRecord.objects.filter(date=today))
        self.assertEqual(records, all_today)

    def test_successive_no_change(self, mocked_actuals):
        today = datetime.date.today()
        mocked_actuals.return_value = (
            Actual(
                volunteer=self.vols[0],
                job=self.jobs[0],
                date=today,
                original=self.vols[0],
                is_substitution=False,
            ),
            Actual(
                volunteer=self.vols[1],
                job=self.jobs[1],
                date=today,
                original=self.vols[2],
                is_substitution=True,
            ),
            Actual(
                volunteer=None,
                job=self.jobs[1],
                date=today,
                original=None,
                is_substitution=True,
            ),
        )
        for _ in range(5):
            response = self.client.get(reverse("cron_daily"))
            records = {
                VolunteerRecord.objects.get(
                    volunteer=self.vols[0],
                    job=self.jobs[0],
                    date=today,
                    original=self.vols[0],
                    is_substitution=False,
                ),
                VolunteerRecord.objects.get(
                    volunteer=self.vols[1],
                    job=self.jobs[1],
                    date=today,
                    original=self.vols[2],
                    is_substitution=True,
                ),
                VolunteerRecord.objects.get(
                    volunteer=None,
                    job=self.jobs[1],
                    date=today,
                    original=None,
                    is_substitution=True,
                ),
            }
            all_today = set(VolunteerRecord.objects.filter(date=today))
            self.assertEqual(records, all_today)

    def test_successive_with_change(self, mocked_actuals):
        today = datetime.date.today()
        for i in range(5):
            mocked_actuals.return_value = (
                Actual(
                    volunteer=self.vols[i],
                    job=self.jobs[i],
                    date=today,
                    original=self.vols[i],
                    is_substitution=False,
                ),
                Actual(
                    volunteer=self.vols[i + 1],
                    job=self.jobs[i + 1],
                    date=today,
                    original=self.vols[i + 2],
                    is_substitution=True,
                ),
                Actual(
                    volunteer=None,
                    job=self.jobs[i + 1],
                    date=today,
                    original=None,
                    is_substitution=True,
                ),
                Actual(
                    volunteer=self.vols[2],
                    job=self.jobs[3],
                    date=today,
                    original=self.vols[3 + i // 2],
                    is_substitution=True,
                ),
            )
            response = self.client.get(reverse("cron_daily"))
            records = {
                VolunteerRecord.objects.get(
                    volunteer=self.vols[i],
                    job=self.jobs[i],
                    date=today,
                    original=self.vols[i],
                    is_substitution=False,
                ),
                VolunteerRecord.objects.get(
                    volunteer=self.vols[i + 1],
                    job=self.jobs[i + 1],
                    date=today,
                    original=self.vols[i + 2],
                    is_substitution=True,
                ),
                VolunteerRecord.objects.get(
                    volunteer=None,
                    job=self.jobs[i + 1],
                    date=today,
                    original=None,
                    is_substitution=True,
                ),
                VolunteerRecord.objects.get(
                    volunteer=self.vols[2],
                    job=self.jobs[3],
                    date=today,
                    original=self.vols[3 + i // 2],
                    is_substitution=True,
                ),
            }
            all_today = set(VolunteerRecord.objects.filter(date=today))
            self.assertEqual(records, all_today)


class TestCronDeletions(TestCase):
    __author__ = "Josh Santana"

    @patch("interfaces.address_lookup.validate",
           lambda *a, **k: {"lat": None, "lng": None})
    def setUp(self):
        # set up customer, payment, route,
        self.client = Client()
        self.client.force_login(
            User.objects.get_or_create(
                username="admin",
                password="pass@123",
                email="admin@admin.com",
                is_staff=True,
            )[0])

        self.payment = Payment.objects.create(name="testpayment")
        job_type = JobType.objects.create(name="test_type")
        self.route = Route.objects.create(
            description="testroute desc", number="1", job_type=job_type
        )

        self.user = User.objects.get(username="admin")
        self.customer = Customer.objects.create(
            route=self.route,
            join_date="1999-12-11",
            pays=self.payment,
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
            num_weekend_meals="2",
            meal_recurrence=serialize(
                Recurrence(Rule(freq=WEEKLY, byday=(MO, TU, WE, TH, FR)))
            ),
        )
        self.volunteer = Volunteer.objects.get(user__username="admin")
        self.job = Job.objects.create(name="job", job_type=job_type,)
        self.assignment = Assignment.objects.create(
            volunteer=self.volunteer, job=self.job, day_of_week=1, week_of_month=1, )

    @freeze_time("2020-03-15")
    def test_customer_record(self):
        # one to delete
        CustomerRecord.objects.create(
            customer=self.customer,
            date=datetime.date(year=2019, month=3, day=15),
            num_meals=1,
            payment_type=self.payment,
            route_assigned=self.route,
        )
        # one to keep
        CustomerRecord.objects.create(
            customer=self.customer,
            date=datetime.date.today() -
            datetime.timedelta(
                days=RETENTION -
                1),
            num_meals=1,
            payment_type=self.payment,
            route_assigned=self.route,
        )
        # run the job
        response = self.client.get(reverse("cron_daily"))
        self.assertEqual(response.status_code, 200)

        # did it get deleted?
        with self.assertRaises(CustomerRecord.DoesNotExist):
            CustomerRecord.objects.get(
                customer=self.customer,
                date=datetime.date(year=2019, month=3, day=15),
                num_meals=1,
                payment_type=self.payment,
                route_assigned=self.route,
            )
        # did it keep?
        CustomerRecord.objects.get(
            customer=self.customer,
            date=datetime.date.today() -
            datetime.timedelta(
                days=RETENTION -
                1),
            num_meals=1,
            payment_type=self.payment,
            route_assigned=self.route,
        )

    @freeze_time("2020-03-15")
    def test_volunteer_record(self):
        # one to delete
        VolunteerRecord.objects.create(
            volunteer=self.volunteer,
            job=self.job,
            date=datetime.date(year=2019, month=3, day=15),
            is_substitution=False,
        )
        # one to keep
        VolunteerRecord.objects.create(
            volunteer=self.volunteer,
            job=self.job,
            date=datetime.date.today() -
            datetime.timedelta(
                days=RETENTION -
                1),
            is_substitution=False,
        )
        # run the job
        response = self.client.get(reverse("cron_daily"))
        self.assertEqual(response.status_code, 200)

        # did it get deleted?
        with self.assertRaises(VolunteerRecord.DoesNotExist):
            VolunteerRecord.objects.get(
                volunteer=self.volunteer,
                job=self.job,
                date=datetime.date(year=2019, month=3, day=15),
                is_substitution=False,
            )
        # did it keep?
        VolunteerRecord.objects.get(
            volunteer=self.volunteer,
            job=self.job,
            date=datetime.date.today() -
            datetime.timedelta(
                days=RETENTION -
                1),
            is_substitution=False,
        )

    @freeze_time("2020-03-15")
    def test_substitution(self):
        # one to delete
        Substitution.objects.create(
            volunteer=self.volunteer,
            assignment=self.assignment,
            date=datetime.date(year=2019, month=3, day=15),
        )
        # one to keep
        Substitution.objects.create(
            volunteer=self.volunteer,
            assignment=self.assignment,
            date=datetime.date.today() -
            datetime.timedelta(
                days=RETENTION -
                1),
        )
        # run the job
        response = self.client.get(reverse("cron_daily"))
        self.assertEqual(response.status_code, 200)

        # did it get deleted?
        with self.assertRaises(Substitution.DoesNotExist):
            Substitution.objects.get(
                volunteer=self.volunteer,
                assignment=self.assignment,
                date=datetime.date(year=2019, month=3, day=15),
            )
        # did it keep?
        Substitution.objects.get(
            volunteer=self.volunteer,
            assignment=self.assignment,
            date=datetime.date.today() -
            datetime.timedelta(
                days=RETENTION -
                1),
        )

    @freeze_time("2020-03-15")
    def test_daterange(self):
        # one to delete
        DateRange.objects.create(
            customer=self.customer,
            start_date=datetime.date(year=2019, month=3, day=14),
            end_date=datetime.date(year=2019, month=3, day=15),
        )
        # one to keep
        DateRange.objects.create(
            customer=self.customer,
            start_date=datetime.date.today() -
            datetime.timedelta(
                days=RETENTION -
                2),
            end_date=datetime.date.today() -
            datetime.timedelta(
                days=RETENTION -
                1),
        )
        # run the job
        response = self.client.get(reverse("cron_daily"))
        self.assertEqual(response.status_code, 200)

        # did it get deleted?
        with self.assertRaises(DateRange.DoesNotExist):
            DateRange.objects.get(
                customer=self.customer,
                start_date=datetime.date(year=2019, month=3, day=14),
                end_date=datetime.date(year=2019, month=3, day=15),
            )
        # did it keep?
        DateRange.objects.get(
            customer=self.customer,
            start_date=datetime.date.today() -
            datetime.timedelta(
                days=RETENTION -
                2),
            end_date=datetime.date.today() -
            datetime.timedelta(
                days=RETENTION -
                1),
        )

    @freeze_time("2020-03-15")
    def test_announcement(self):
        # one to delete
        ManagerAnnouncement.objects.create(
            created_by=self.volunteer,
            display_until=datetime.date(year=2019, month=3, day=15),
            announcement="HELLO",
        )
        # one to keep
        ManagerAnnouncement.objects.create(
            created_by=self.volunteer,
            display_until=datetime.date.today() -
            datetime.timedelta(
                days=RETENTION -
                1),
            announcement="HELLO",
        )
        # run the job
        response = self.client.get(reverse("cron_daily"))
        self.assertEqual(response.status_code, 200)

        # did it get deleted?
        with self.assertRaises(ManagerAnnouncement.DoesNotExist):
            ManagerAnnouncement.objects.get(
                created_by=self.volunteer,
                display_until=datetime.date(year=2019, month=3, day=15),
                announcement="HELLO",
            )
        # did it keep?
        ManagerAnnouncement.objects.get(
            created_by=self.volunteer,
            display_until=datetime.date.today() -
            datetime.timedelta(
                days=RETENTION -
                1),
            announcement="HELLO",
        )
