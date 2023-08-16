import datetime
from unittest import SkipTest

# https://docs.python.org/3/library/unittest.mock.html
from unittest.mock import patch

from django.contrib.auth.models import User
from django.http import FileResponse, HttpResponse
from django.test import Client, TestCase
from django.urls import reverse
from freezegun import freeze_time
from recurrence import serialize

from interfaces.recurrence import (
    FR,
    MO,
    TH,
    TU,
    WE,
    WEEKLY,
    Recurrence,
    Rule,
    date_to_day_of_month,
)
from meals.constants import (
    OPEN_ROUTE,
    OPEN_SUBSTITUTION,
    RETENTION,
    ROUTE_TYPE_NAME,
    UNASSIGNED_JOB,
)
from models.models import (
    Actual,
    Assignment,
    Customer,
    CustomerRecord,
    DateRange,
    Diet,
    Job,
    JobType,
    ManagerAnnouncement,
    Payment,
    Pet,
    PetFood,
    Route,
    Substitution,
    User,
    Volunteer,
    VolunteerRecord,
)
from pdfs.views import monthly_billing_report


class TestCustomerMealReports(TestCase):
    __author__ = "Max Patek"

    def cron_on_day(self, day):
        with freeze_time(day):
            self.client.get(reverse("cron_daily"))

    @patch("interfaces.address_lookup.validate")
    def setUp(self, mocked_validate):
        mocked_validate.return_value = {"lat": None, "lng": None}
        self.client = Client()
        self.client.force_login(
            User.objects.get_or_create(
                username="admin",
                password="pass@123",
                email="admin@admin.com",
                is_staff=True,
            )[0])
        self.diets = [
            Diet.objects.create(
                name=f"Diet{i}",
                code=f"D{i}") for i in range(4)]
        self.payments = [
            Payment.objects.create(
                name=f"Pays{i}",
            ) for i in range(4)]
        self.routes = [
            Route.objects.create(
                name=f"Route {i}",
                number=i,
                job_type=JobType.objects.get_or_create(name=ROUTE_TYPE_NAME)[0],
            )
            for i in range(4)
        ]
        self.mwf_customers = [
            Customer.objects.create(
                first_name=f"Customer{i}",
                last_name=f"MWF",
                route=self.routes[i % len(self.routes)],
                pays=self.payments[i % len(self.payments)],
                diet=self.diets[i % len(self.diets)],
                hot_diet_restrictions=f"hot{i}",
                cold_diet_restrictions=f"cold{i}",
                address="some address",
                notes="notes",
                meal_recurrence=serialize(Recurrence(Rule(freq=WEEKLY, byday=(MO, WE, FR)))),
                num_weekend_meals=i,
                active=True,
            )
            for i in range(10)
        ]
        self.tuth_customers = [
            Customer.objects.create(
                first_name=f"Customer{i}",
                last_name=f"TuTh",
                route=self.routes[i % len(self.routes)],
                pays=self.payments[i % len(self.payments)],
                diet=self.diets[i % len(self.diets)],
                hot_diet_restrictions=f"hot{i}",
                cold_diet_restrictions=f"cold{i}",
                address="some address",
                notes="notes",
                meal_recurrence=serialize(Recurrence(Rule(freq=WEEKLY, byday=(TU, TH)))),
                num_weekend_meals=0,
                active=True,
            )
            for i in range(10)
        ]
        self.inactive_customers = [
            Customer.objects.create(
                first_name=f"Customer{i}",
                last_name=f"Inactive",
                route=self.routes[i % len(self.routes)],
                pays=self.payments[i % len(self.payments)],
                diet=self.diets[i % len(self.diets)],
                hot_diet_restrictions=f"hot{i}",
                cold_diet_restrictions=f"cold{i}",
                address="some address",
                notes="notes",
                meal_recurrence=serialize(
                    Recurrence(Rule(freq=WEEKLY, byday=(MO, TU, WE, TH, FR)))
                ),
                num_weekend_meals=i,
                active=False,
            )
            for i in range(10)
        ]
        self.dateranged_customers = [
            Customer.objects.create(
                first_name=f"Customer{i}",
                last_name=f"DateRanged",
                route=self.routes[i % len(self.routes)],
                pays=self.payments[i % len(self.payments)],
                diet=self.diets[i % len(self.diets)],
                hot_diet_restrictions=f"hot{i}",
                cold_diet_restrictions=f"cold{i}",
                address="some address",
                notes="notes",
                meal_recurrence=serialize(
                    Recurrence(Rule(freq=WEEKLY, byday=(MO, TU, WE, TH, FR)))
                ),
                num_weekend_meals=i,
                active=False,
            )
            for i in range(10)
        ]
        self.date_ranges = [
            DateRange.objects.create(
                customer=cust,
                start_date=datetime.date(year=1970, month=1, day=1),
                end_date=datetime.date(year=2050, month=1, day=1),
            )
            for cust in self.dateranged_customers
        ]
        self.friday_str = "03-27-2020"
        self.thursday_str = "03-26-2020"
        self.wednesday_str = "03-25-2020"

    @freeze_time("2020-3-25")
    def test_labels(self):
        response = self.client.get(f"/pdfs/labels/{self.friday_str}/")
        for i, cust in enumerate(self.mwf_customers):
            self.assertContains(response, cust, count=1 + i)
            self.assertContains(
                response,
                cust.hot_diet_restrictions,
                count=1 + i)
            self.assertContains(
                response,
                cust.cold_diet_restrictions,
                count=1 + i)
        for cust in self.inactive_customers + \
                self.dateranged_customers + self.tuth_customers:
            self.assertNotContains(response, cust)
        for i, diet in enumerate(self.diets):
            self.assertContains(
                response,
                diet,
                count=sum(
                    1 +
                    j for j in range(
                        i,
                        10,
                        4)))
        for i, route in enumerate(self.routes):
            self.assertContains(
                response,
                route.name,
                count=sum(
                    1 +
                    j for j in range(
                        i,
                        10,
                        4)))
        response = self.client.get(f"/pdfs/labels/{self.thursday_str}/")
        for cust in self.tuth_customers:
            self.assertContains(response, cust, count=1)
            self.assertContains(response, cust.hot_diet_restrictions, count=1)
            self.assertContains(response, cust.cold_diet_restrictions, count=1)
        for cust in self.inactive_customers + \
                self.dateranged_customers + self.mwf_customers:
            self.assertNotContains(response, cust)
        for i, diet in enumerate(self.diets):
            self.assertContains(response, diet, count=2 + (i <= 1))
        for i, route in enumerate(self.routes):
            self.assertContains(response, route.name, count=2 + (i <= 1))

    @freeze_time("2020-3-26")
    @patch("pdfs.views.to_pdf", lambda html: HttpResponse(html))
    def test_monthly_billing_normal_day(self):
        today = datetime.date.today()
        self.cron_on_day("2020-3-26")
        response = self.client.get(
            f"/pdfs/monthly-billing-report/{self.thursday_str}/{self.thursday_str}/"
        )
        for i, cust in enumerate(self.tuth_customers):
            self.assertContains(
                response,
                f"<td>{cust}</td> <td> {1} </td> <td>{cust.pays}</td> <td>{cust.route}</td>",
                html=True,
            )
        for i, pay in enumerate(self.payments):
            self.assertContains(
                response,
                f"{pay}: {2+(i<=1)} meals for {2+(i<=1)} clients",
                html=True)
        self.assertContains(
            response,
            f"<td>{ today.strftime('%B %d, %Y') } </td> <td>{10}</td>",
            html=True)
        self.assertContains(response, f"Total Meals: {10} ", html=True)

    @freeze_time("2020-3-27")
    @patch("pdfs.views.to_pdf", lambda html: HttpResponse(html))
    def test_monthly_billing_weekend_meals(self):
        today = datetime.date.today()
        self.cron_on_day("2020-3-27")
        response = self.client.get(
            f"/pdfs/monthly-billing-report/{self.friday_str}/{self.friday_str}/"
        )
        for i, cust in enumerate(self.mwf_customers):
            self.assertContains(
                response,
                f"<td>{cust}</td> <td> {1+i} </td> <td>{cust.pays}</td> <td>{cust.route}</td>",
                html=True,
            )
        for i, pay in enumerate(self.payments):
            self.assertContains(
                response,
                f"{pay}: {sum(range(1+i, 11, 4))} meals for {2+(i<=1)} clients",
                html=True,
            )
        self.assertContains(
            response,
            f"<td>{ today.strftime('%B %d, %Y') } </td> <td>{sum(range(1, 11))}</td>",
            html=True,
        )
        self.assertContains(
            response,
            f"Total Meals: {sum(range(1, 11))} ",
            html=True)

    @freeze_time("2020-3-27")
    @patch("pdfs.views.to_pdf", lambda html: HttpResponse(html))
    def test_monthly_billing_multiple_days(self):
        wednesday = datetime.date.today() - datetime.timedelta(days=2)
        thursday = datetime.date.today() - datetime.timedelta(days=1)
        friday = datetime.date.today()
        self.cron_on_day("2020-3-25")
        self.cron_on_day("2020-3-26")
        self.cron_on_day("2020-3-27")
        response = self.client.get(
            f"/pdfs/monthly-billing-report/{self.wednesday_str}/{self.friday_str}/"
        )
        for i, cust in enumerate(self.mwf_customers):
            self.assertContains(
                response,
                f"<td>{cust}</td> <td> {2+i} </td> <td>{cust.pays}</td> <td>{cust.route}</td>",
                html=True,
            )
        for i, cust in enumerate(self.tuth_customers):
            self.assertContains(
                response,
                f"<td>{cust}</td> <td> {1} </td> <td>{cust.pays}</td> <td>{cust.route}</td>",
                html=True,
            )
        for i, pay in enumerate(self.payments):
            self.assertContains(
                response,
                f"{pay}: {sum(range(2+i, 12, 4)) + 2+(i<=1)} meals for {2*(2+(i<=1))} clients",
                html=True,
            )
        self.assertContains(
            response,
            f"<td>{ wednesday.strftime('%B %d, %Y') } </td> <td>{10}</td>",
            html=True)
        self.assertContains(
            response,
            f"<td>{ thursday.strftime('%B %d, %Y') } </td> <td>{10}</td>",
            html=True)
        self.assertContains(
            response,
            f"<td>{ friday.strftime('%B %d, %Y') } </td> <td>{sum(range(1, 11))}</td>",
            html=True,
        )
        self.assertContains(
            response,
            f"Total Meals: {sum(range(1, 11)) + 20} ",
            html=True)

    @patch("pdfs.views.to_pdf", lambda html: HttpResponse(html))
    def test_daily_count(self):
        # dietless = Customer.objects.create(
        #     first_name=f"Customer",
        #     last_name=f"Dietless",
        #     diet=None,
        #     address="some address",
        #     meal_recurrence=serialize(Recurrence(Rule(freq=WEEKLY, byday=(MO, WE, FR)))),
        #     num_weekend_meals=1,
        #     active=True,
        # )
        # response = self.client.get(f"/pdfs/daily-count-report/{self.friday_str}/")
        # for i, diet in enumerate(self.diets):
        #     self.assertContains(
        #         response,
        #         f'<td style="width:80%">{diet} ({diet.code})</td> <td>{sum(range(1+i, 11, 4))}</td>',
        #         html=True,
        #     )
        # self.assertContains(
        #     response, f"<td>+Frozen</td> <td>{sum(range(10)) + 1}</td>", html=True,
        # )
        # self.assertContains(
        #     response,
        #     f"<td><b>Total</b></td> <td><b>{sum(range(1, 11)) + 2}</b></td>",
        #     html=True,
        # )
        raise SkipTest

    @patch("pdfs.views.to_pdf", lambda html: HttpResponse(html))
    @freeze_time("2020-3-27")
    def test_generate_routes(self):
        today = datetime.date.today()
        response = self.client.get(
            f"/pdfs/generate-routes-report/{self.friday_str}/")
        html = "\n".join(str(response.content).split("\\n"))
        for i, route in enumerate(self.routes):
            custs = [c for c in self.mwf_customers if c.route == route]

            waypoints = "\n".join(
                f"""
                    <tr>
                        <td>{ci + 1}</td>
                        <td>{c}</td>
                        <td>{c.address}</td>
                        <td>{c.printed_notes}</td>
                        <td>{c.diet.code}</td>
                        <td>{c.num_meals_on_day(today)}</td>
                    </tr>"""
                for ci, c in enumerate(custs)
            )
            expected = f"""
                <p style="text-align:right"><em>Questions? Call: (434) 293-4364</em></p>
                <h4><b>{route} | {today.strftime("%B %d, %Y")} | Volunteer(s): | Meals: {sum(range(1+i, 11, 4))}</b></h4>
                <table class="table table-condensed">
                    <thead>
                            <tr>
                                <th>Order</th>
                                <th>Name</th>
                                <th>Address</th>
                                <th>Notes</th>
                                <th>Diet</th>
                                <th>Meals</th>
                            </tr>
                    </thead>
                    <tbody>
                        {waypoints}
                    </tbody>
                </table>
                <div class="page-break">.</div>"""
            self.assertIn("".join(expected.split()), "".join(html.split()))

            # doesn't work for some reason:
            # self.assertContains(response, expected, html=True)


@freeze_time("2020-3-25")
@patch("pdfs.views.to_pdf", lambda html: HttpResponse(html))
class TestJobReports(TestCase):
    __author__ = "Max Patek"

    def setUp(self):
        """
        For brevity, stealing the setup of TestCustomerMealReports.
        This includes:

        self.diets 0..3
        self.payments 0..3
        self.routes 0..3
        self.mwf_customers 0..9
        self.tuth_customers 0..9
        self.inactive_customers 0..9
        self.dateranged_customers 0..9
        self.date_ranges 0..9
        self.friday_str 03-27-2020
        self.thursday_str 03-26-2020
        self.wednesday_str 03-25-2020
        """
        TestCustomerMealReports.setUp(self)  # reuse previous setup
        self.users = [
            User.objects.create(
                username=f"user{i}",
                first_name=f"First{i}",
                last_name="Last",
            ) for i in range(10)]
        self.vols = [Volunteer.objects.get(user=user) for user in self.users]
        self.friday = datetime.date.today() + datetime.timedelta(days=2)
        self.thursday = datetime.date.today() + datetime.timedelta(days=1)
        self.friday_dom = date_to_day_of_month(self.friday)
        self.thursday_dom = date_to_day_of_month(self.thursday)
        self.assignments = [  # friday is assigned
            Assignment.objects.create(
                volunteer=self.vols[i],
                job=self.routes[i],
                day_of_week=self.friday_dom.day_of_week,
                week_of_month=self.friday_dom.week_of_month,
            )
            for i in range(3)
        ] + [  # thursday is all open route
            Assignment.objects.create(
                volunteer=None,
                job=self.routes[i],
                day_of_week=self.thursday_dom.day_of_week,
                week_of_month=self.thursday_dom.week_of_month,
            )
            for i in range(3)
        ]
        self.friday_filled_sub = Substitution.objects.create(
            date=self.friday,
            volunteer=self.vols[-1],
            assignment=Assignment.objects.get(
                job__route__number=1,
                day_of_week=self.friday_dom.day_of_week,
                week_of_month=self.friday_dom.week_of_month,
            ),
        )
        self.friday_open_sub = Substitution.objects.create(
            date=self.friday,
            volunteer=None,
            assignment=Assignment.objects.get(
                job__route__number=2,
                day_of_week=self.friday_dom.day_of_week,
                week_of_month=self.friday_dom.week_of_month,
            ),
        )
        self.thursday_filled_sub = Substitution.objects.create(
            date=self.thursday,
            volunteer=self.vols[-1],
            assignment=Assignment.objects.get(
                job__route__number=1,
                day_of_week=self.thursday_dom.day_of_week,
                week_of_month=self.thursday_dom.week_of_month,
            ),
        )
        self.thursday_open_sub = Substitution.objects.create(
            date=self.thursday,
            volunteer=None,
            assignment=Assignment.objects.get(
                job__route__number=2,
                day_of_week=self.thursday_dom.day_of_week,
                week_of_month=self.thursday_dom.week_of_month,
            ),
        )
        self.substitutions = [
            self.friday_filled_sub,
            self.friday_open_sub,
            self.thursday_filled_sub,
            self.thursday_open_sub,
        ]

    def test_substitutions(self):
        response = self.client.get(
            f"/pdfs/substitutions-report/{self.thursday_str}/{self.friday_str}/"
        )
        for sub in self.substitutions:
            self.assertContains(
                response,
                f"""
                    <td class="col-xs-4">{sub.assignment.job.name}</td>
                    <td class="col-xs-4">{sub.assignment.volunteer or OPEN_ROUTE}</td>
                    <td class="col-xs-4">{sub.volunteer or OPEN_SUBSTITUTION}</td>
                """,
                html=True,
            )

    def test_job_overview(self):
        response = self.client.get(
            f"/pdfs/job-overview-report/{self.thursday_str}/{self.friday_str}/"
        )
        for route in self.routes:
            self.assertContains(response, route, count=2)
        for vol in self.vols[:3]:
            self.assertContains(response, vol, count=1)
        self.assertContains(response, self.vols[-1], count=2)
        self.assertContains(response, OPEN_ROUTE, count=3)
        self.assertContains(response, OPEN_SUBSTITUTION, count=2)
        self.assertContains(response, UNASSIGNED_JOB, count=2)


@freeze_time("2020-3-25")
@patch("pdfs.views.to_pdf", lambda html: HttpResponse(html))
@patch("interfaces.address_lookup.validate",
       lambda *a, **k: {"lat": None, "lng": None})
class TestSpecialDates(TestCase):
    __author__ = "Max Patek"

    def setUp(self):
        self.client = Client()
        self.client.force_login(
            User.objects.get_or_create(
                username="admin",
                password="pass@123",
                email="admin@admin.com",
                is_staff=True,
            )[0])

    def every_day_in_a_month(self, year, month):
        for day in range(1, 32):
            try:
                date = datetime.date(year=year, month=month, day=day)
            except ValueError:
                break
            yield date

    def bunch_of_dates(self):
        for year in range(1950, 1953):
            for month in range(1, 12):
                yield from self.every_day_in_a_month(year, month)

    def test_client_birthday(self):
        month = 6
        custs = []
        job_type = JobType.objects.create(name="route_job_type")
        route = Route.objects.create(
            description="This route is required for the client to show up on the report.",
            number=1,
            job_type=job_type)
        for date in self.bunch_of_dates():
            cust = Customer.objects.create(
                first_name="Born on",
                last_name=str(date),
                birth_date=date,
                address="",
                route=route,
            )
            if date.month == month:
                custs.append(cust)
        response = self.client.get(f"/pdfs/client-birthday-report/{month}/")
        for cust in custs:
            self.assertContains(response, cust)

    def test_volunteer_brithday(self):
        month = 6
        vols = []
        for date in self.bunch_of_dates():
            user = User.objects.create(
                username=f"born{date}",
                first_name="Born on",
                last_name=str(date),
            )
            vol = Volunteer.objects.get(user=user)
            vol.birth_date = date
            vol.save()
            if date.month == month:
                vols.append(vol)
        response = self.client.get(f"/pdfs/volunteer-birthday-report/{month}/")
        for vol in vols:
            self.assertContains(response, vol)

    def test_volunteer_join_date(self):
        vols = []
        for date in self.bunch_of_dates():
            user = User.objects.create(
                username=f"joined{date}",
                first_name="Joined on",
                last_name=str(date),
            )
            vol = Volunteer.objects.get(user=user)
            vol.join_date = date
            vol.save()
            vols.append(vol)
        response = self.client.get("/pdfs/volunteer-join-date-report")
        for vol in vols:
            self.assertContains(response, vol)


class TestPDFs(TestCase):
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

    def test_join_date_report_returns_pdf(self):
        """ This test checks that the join date report returns a pdf """
        __author__ = "Nate Strawser"
        now = datetime.date.today()
        response = self.client.get("/pdfs/volunteer-join-date-report")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_daily_count_report_returns_pdf(self):
        """ This test checks that the daily count report """
        __author__ = "Nate Strawser"
        now = datetime.date.today()
        date_string = now.strftime("%m-%d-%Y")
        response = self.client.get(f"/pdfs/daily-count-report/{date_string}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_monthly_billing_returns_pdf(self):
        __author__ = "Kevin Naddoni"

        day = datetime.date(year=2020, month=2, day=4)
        date_string = day.strftime("%m-%d-%Y")
        response = self.client.get(f"/pdfs/daily-count-report/{date_string}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_generate_route_returns_pdf(self):
        __author__ = "Kevin Naddoni"

        response = self.client.get(f"/pdfs/generate-routes-report/03-13-2020/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")


class TestPetLabels(TestCase):
    __author__ = "Kevin Naddoni"

    def cron_on_day(self, day):
        with freeze_time(day):
            self.client.get(reverse("cron_daily"))

    @patch("interfaces.address_lookup.validate")
    def setUp(self, mocked_validate):
        mocked_validate.return_value = {"lat": None, "lng": None}
        self.client = Client()
        self.client.force_login(
            User.objects.get_or_create(
                username="admin",
                password="pass@123",
                email="admin@admin.com",
                is_staff=True,
            )[0])
        self.pet_foods = [
            PetFood.objects.create(
                name=f"PetFood{i}",
                code=f"P{i}") for i in range(4)]
        self.pets = [Pet.objects.create(name=f"Pet{i}",) for i in range(4)]
        self.payments = [
            Payment.objects.create(
                name=f"Pays{i}",
            ) for i in range(4)]
        self.diets = [
            Diet.objects.create(
                name=f"Diet{i}",
                code=f"D{i}") for i in range(4)]
        self.routes = [
            Route.objects.create(
                name=f"Route {i}",
                number=i,
                job_type=JobType.objects.get_or_create(name=ROUTE_TYPE_NAME)[0],
            )
            for i in range(4)
        ]
        self.mwf_customers = [
            Customer.objects.create(
                first_name=f"Customer{i}",
                last_name=f"MWF",
                route=self.routes[i % len(self.routes)],
                pays=self.payments[i % len(self.payments)],
                diet=self.diets[i % len(self.diets)],
                hot_diet_restrictions=f"hot{i}",
                cold_diet_restrictions=f"cold{i}",
                address="some address",
                notes="notes",
                pet=self.pets[i % len(self.pets)],
                petfood=self.pet_foods[i % len(self.pet_foods)],
                meal_recurrence=serialize(Recurrence(Rule(freq=WEEKLY, byday=(MO, WE, FR)))),
                num_weekend_meals=i,
                active=True,
            )
            for i in range(10)
        ]
        self.tuth_customers = [
            Customer.objects.create(
                first_name=f"Customer{i}",
                last_name=f"TuTh",
                route=self.routes[i % len(self.routes)],
                pays=self.payments[i % len(self.payments)],
                diet=self.diets[i % len(self.diets)],
                hot_diet_restrictions=f"hot{i}",
                cold_diet_restrictions=f"cold{i}",
                address="some address",
                notes="notes",
                pet=self.pets[i % len(self.pets)],
                petfood=self.pet_foods[i % len(self.pet_foods)],
                meal_recurrence=serialize(Recurrence(Rule(freq=WEEKLY, byday=(TU, TH)))),
                num_weekend_meals=0,
                active=True,
            )
            for i in range(10)
        ]
        self.friday_str = "03-27-2020"
        self.thurs_str = "03-26-2020"

    @freeze_time("2020-3-25")
    def test_pet_labels(self):
        response = self.client.get(f"/pdfs/pet-labels/{self.friday_str}/")
        for cust in self.mwf_customers:
            self.assertContains(response, cust, count=1)
        for i, pet in enumerate(self.pets):
            self.assertContains(response, pet, count=2 * (2 + (i <= 1)))
        for i, petfood in enumerate(self.pet_foods):
            self.assertContains(response, petfood, count=2 * (2 + (i <= 1)))

        response = self.client.get(f"/pdfs/pet-labels/{self.thurs_str}/")
        for cust in self.tuth_customers:
            self.assertContains(response, cust, count=1)
        for i, pet in enumerate(self.pets):
            self.assertContains(response, pet, count=2 * (2 + (i <= 1)))
        for i, petfood in enumerate(self.pet_foods):
            self.assertContains(response, petfood, count=2 * (2 + (i <= 1)))
