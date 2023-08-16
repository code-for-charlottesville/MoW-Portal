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


class TestIndexPage(TestCase):
    def setUp(self):
        client = Client()
        # login as staff
        self.client.force_login(
            User.objects.get_or_create(
                username="admin",
                password="pass@123",
                email="admin@admin.com",
                is_staff=True,
            )[0])
        # create a volunteer
        user = User.objects.get_or_create(
            username="volunteer",
            first_name="firstname",
            last_name="lastname",
            password="mealsonwheels",
        )[0]
        self.vol = Volunteer.objects.get(user=user)
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
            date=day, assignment=assignment, volunteer=None)

    def test_not_logged_in_index(self):
        """ ensure the redirect works properly """
        self.client.logout()
        response = self.client.get("/staff/")
        self.assertEqual(response.status_code, 302)

    def test_get_index_page_open_sub(self):
        """ simple get request to the page """
        response = self.client.get("/staff/")
        self.assertEqual(response.status_code, 200)
        # weekend days should not be included
        self.assertNotContains(response, "Saturday")
        self.assertNotContains(response, "Sunday")
        self.assertContains(response, "packer needs a sub.")

    def test_get_index_page_filled_sub(self):
        """ simple get request to the page """
        self.sub.volunteer = self.vol
        self.sub.save()  # save changes
        response = self.client.get("/staff/")
        self.assertEqual(response.status_code, 200)
        # weekend days should not be included
        self.assertNotContains(response, "Saturday")
        self.assertNotContains(response, "Sunday")
        self.assertNotContains(response, "packer needs a sub.")
        self.assertTrue(b"There are no announcements.")

    def test_display_announcement(self):
        """ test for announcements rendering """
        day = datetime.date.today()
        announcement = ManagerAnnouncement.objects.create(
            announcement="Today's announcements", display_until=day
        )
        response = self.client.get("/staff/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Today's announcements")
