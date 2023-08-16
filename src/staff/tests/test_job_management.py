import datetime

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from freezegun import freeze_time

from interfaces.recurrence import abbreviated_days_of_week, abbreviated_weeks_of_month
from meals.constants import OPEN_ROUTE
from models.models import (
    Assignment,
    Customer,
    Job,
    JobType,
    ManagerAnnouncement,
    Route,
    Substitution,
    Volunteer,
)
from staff import views
from staff.views.email import send_email


@freeze_time("2020-03-13")
class TestManageJobs(TestCase):
    def setUp(self):
        client = Client()
        self.client.force_login(
            User.objects.get_or_create(
                username="admin",
                password="pass@123",
                email="admin@admin.com",
                is_staff=True,
            )[0])
        JobType.objects.get_or_create(name="Route")

    def test_display_today_redirect(self):
        """
        test that the page redirects to today's url when passed nothing
        """
        day = datetime.date.today()
        response = self.client.get("/staff/manage-jobs/")
        # should redirect to url showing today's date
        self.assertRedirects(
            response, "/staff/manage-jobs/{}/".format(day.strftime("%m-%d-%Y"))
        )


class TestJobManagement(TestCase):
    def setUp(self):
        client = Client()
        self.client.force_login(
            User.objects.get_or_create(
                username="admin",
                password="pass@123",
                email="admin@admin.com",
                is_staff=True,
            )[0])
        # login as staff
        user = User.objects.get_or_create(
            username="volunteer",
            first_name="firstname",
            last_name="lastname",
            password="mealsonwheels",
        )[0]
        # create a substitution object
        vol = Volunteer.objects.get(user=user)
        job_type = JobType.objects.create(name="test_type")
        job = Job.objects.create(
            name="packer",
            num_vols_required=1,
            job_type=job_type)
        day = datetime.date.today()
        if day.isoweekday() == 6 or day.isoweekday() == 7:
            day = day + datetime.timedelta(days=2)  # will always be weekday
        week_of_month = (day.day - 1) // 7 + 1
        assignment = Assignment.objects.create(
            job=job, day_of_week=day.isoweekday(), week_of_month=week_of_month
        )
        self.sub = Substitution.objects.create(
            date=day, assignment=assignment, volunteer=vol)

    def test_manage_open_job_assignment_not_found(self):
        """
        test manage_open_job when the assignment pk is not valid
        """
        day = datetime.date.today()
        date_url = day.strftime("%m-%d-%Y")
        # request an invalid primary key, should be 404
        response = self.client.get(
            "/staff/manage-open-job/{}/{}/".format(0, date_url))
        self.assertEqual(response.status_code, 404)

    @freeze_time("2020-03-13")
    def test_manage_open_job_date_not_valid(self):
        """
        make sure it handles the case with a bad date
        """
        day = datetime.date.today()
        week_of_month = (day.day - 1) // 7 + 1
        # need this stuff to create a substitution
        job_type = JobType.objects.get_or_create(name="test_type")[0]
        job = Job.objects.get_or_create(
            name="new-job", num_vols_required=1, job_type=job_type
        )[0]
        assignment = Assignment.objects.get_or_create(
            volunteer=None,
            job=job,
            day_of_week=day.isoweekday(),
            week_of_month=week_of_month,
        )[0]
        response = self.client.get(
            "/staff/manage-open-job/{}/{}/".format(assignment.id, "02-30-2019")
        )
        self.assertRedirects(
            response, "/staff/manage-jobs/{}/".format(day.strftime("%m-%d-%Y"))
        )

    def test_manage_open_job_success(self):
        """
        test for a successful request to create a sub request
        for an open job
        """
        # setup an open job
        day = datetime.date.today()
        # try for every day this week
        for i in range(7):
            day = day + datetime.timedelta(days=i)
            if day.isoweekday() in [6, 7]:
                continue
            date_url = day.strftime("%m-%d-%Y")
            week_of_month = (day.day - 1) // 7 + 1
            # need this stuff to create a substitution
            job_type = JobType.objects.get_or_create(name="test_type")[0]
            job = Job.objects.get_or_create(
                name="new-job", num_vols_required=1, job_type=job_type
            )[0]
            assignment = Assignment.objects.get_or_create(
                volunteer=None,
                job=job,
                day_of_week=day.isoweekday(),
                week_of_month=week_of_month,
            )[0]
            # request the url
            response = self.client.get(
                "/staff/manage-open-job/{}/{}/".format(assignment.id, date_url)
            )
            # see if the substitution has been created by filtering and making
            # sure the count is 1
            sub_count = Substitution.objects.filter(
                assignment=assignment, date=day, volunteer=None
            ).count()
            self.assertEqual(sub_count, 1)
            self.assertRedirects(
                response, "/staff/manage-jobs/{}/".format(date_url))


class TestCreateJob(TestCase):
    def setUp(self):
        client = Client()
        self.client.force_login(
            User.objects.get_or_create(
                username="admin",
                password="pass@123",
                email="admin@admin.com",
                is_staff=True,
            )[0])
        self.route_type = JobType.objects.get_or_create(name="Route")[0]
        self.req_dict = {
            "name": "TEST NAME",
            "num_vols_required": "1",
            "job_type": None,
        }

    @freeze_time("2020-03-17")
    def test_display_past_day(self):
        """
        test that the page can properly bring up a day from the past
        """
        day = datetime.date.today() - datetime.timedelta(days=1)
        response = self.client.get(
            "/staff/manage-jobs/{}/".format(day.strftime("%m-%d-%Y")))
        self.assertContains(response, day.strftime("%A, %B %d, %Y"))

    def test_form_success_non_route(self):
        """
        testing case where the form gets submitted successfully
        and the new job is not a route
        """
        # create the job type and submit the request
        job_type = JobType.objects.get_or_create(name="not_route")
        self.req_dict["job_type"] = job_type[0].pk
        self.req_dict["name"] = "NOT A ROUTE"
        response = self.client.post("/staff/create-job/", self.req_dict)
        # test is was created
        self.assertTrue(Job.objects.filter(name="NOT A ROUTE").count() > 0)

    def test_form_failure_non_route(self):
        """
        case where job is not created because of a form error
        and the new job is not a route
        """
        # won't fail because we are trying to create a job with the same name
        job_type = JobType.objects.get_or_create(name="not_route")
        # job will be in db already
        Job.objects.get_or_create(name="NOT A ROUTE", job_type=job_type[0])
        self.req_dict["job_type"] = job_type[0].pk
        self.req_dict["name"] = "NOT A ROUTE"
        response = self.client.post("/staff/create-job/", self.req_dict)
        self.assertContains(response, "Job with this Name already exists.")

    def test_Form_success_route(self):
        """
        test that the job is created properly when the type is a route
        """
        self.req_dict["job_type"] = self.route_type.pk
        self.req_dict["name"] = "TEST ROUTE"
        # need a route number
        try:
            next_route_number = Route.objects.all().order_by(
                "-number")[0].number + 1
        except IndexError:
            next_route_number = 1
        # add number to request
        self.req_dict["number"] = next_route_number
        response = self.client.post("/staff/create-job/", self.req_dict)
        self.assertTrue(Job.objects.filter(name="TEST ROUTE").count() > 0)
        self.assertTrue(Route.objects.filter(name="TEST ROUTE").count() > 0)

    def test_Form_failure_route(self):
        """
        test that the Route is not created because of a form error
        """
        self.req_dict["job_type"] = self.route_type.pk
        self.req_dict["name"] = "TEST ROUTE"
        # need two route numbers
        try:
            next_route_number = Route.objects.all().order_by(
                "-number")[0].number + 1
        except IndexError:
            next_route_number = 1
        self.req_dict["number"] = next_route_number + 1
        # create a route with the same name then submit
        Route.objects.get_or_create(
            name="TEST ROUTE",
            job_type=self.route_type,
            number=next_route_number)
        response = self.client.post("/staff/create-job/", self.req_dict)
        self.assertContains(response, "Job with this Name already exists.")
