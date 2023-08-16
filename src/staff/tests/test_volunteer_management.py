import datetime
from unittest.mock import patch

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


class TestManageVolunteers(TestCase):
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
        self.vol = Volunteer.objects.get(user=user)

    def test_get_request(self):
        """
        simple get request to the page
        """
        res = self.client.get("/staff/manage-volunteers/")
        self.assertContains(res, "firstname lastname")
        self.assertEqual(res.status_code, 200)


class TestDeleteVolunteer(TestCase):
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
        self.vol = Volunteer.objects.get(user=user)
        self.vol_pk = self.vol.pk
        job_type = JobType.objects.create(name="test_type")
        job = Job.objects.create(
            name="packer",
            num_vols_required=1,
            job_type=job_type)
        day = datetime.date.today()
        week_of_month = (day.day - 1) // 7 + 1
        self.assignment = Assignment.objects.create(
            job=job,
            day_of_week=day.isoweekday(),
            week_of_month=week_of_month,
            volunteer=self.vol,
        )
        assignment_2 = Assignment.objects.create(
            job=job, day_of_week=day.isoweekday(), week_of_month=week_of_month
        )
        self.sub = Substitution.objects.create(
            date=day, assignment=assignment_2, volunteer=self.vol
        )

    def test_404(self):
        """
        should 404 for an invalid pk
        """
        res = self.client.get(f"/staff/delete-volunteer/{0}/")
        self.assertEqual(404, res.status_code)

    def test_delete_volunteer(self):
        """
        should delete the volunteer, make associated assignments open job,
        and open up any filled substitutions
        """
        res = self.client.get(f"/staff/delete-volunteer/{self.vol.pk}/")
        self.assignment.refresh_from_db()
        self.sub.refresh_from_db()
        self.assertIsNone(self.assignment.volunteer)
        self.assertIsNone(self.sub.volunteer)
        with self.assertRaises(Volunteer.DoesNotExist):
            Volunteer.objects.get(pk=self.vol_pk)


class TestEditVolunteer(TestCase):
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
        self.vol = Volunteer.objects.get(user=user)

    def test_get_request(self):
        res = self.client.get(f"/staff/edit-volunteer/{self.vol.pk}/")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Edit Volunteer")

    def test_post_request_invalid_form(self):
        res = self.client.post(
            f"/staff/edit-volunteer/{self.vol.pk}/", {}, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Edit Volunteer")

    def test_post_request_valid_form(self):
        arg = {
            "username": "new_username",
            "first_name": self.vol.user.first_name,
            "last_name": self.vol.user.last_name,
            "email": self.vol.user.email,
            "is_staff": self.vol.user.is_staff,
            "join_date": "2020-03-29",
            "address": "new address",
        }
        res = self.client.post(
            f"/staff/edit-volunteer/{self.vol.pk}/",
            arg,
            follow=True)
        self.vol.refresh_from_db()
        self.vol.user.refresh_from_db()
        self.assertEqual(self.vol.user.username, "new_username")
        self.assertEqual(str(self.vol.address), "new address")
        self.assertRedirects(res, "/staff/manage-volunteers/")


class TestCreateVolunteer(TestCase):
    def setUp(self):
        client = Client()
        self.client.force_login(
            User.objects.get_or_create(
                username="admin",
                password="pass@123",
                email="admin@admin.com",
                is_staff=True,
            )[0])

    def test_get_request(self):
        res = self.client.get("/staff/create-volunteer/")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Create Volunteer")

    def test_invalid_post_request(self):
        res = self.client.post("/staff/create-volunteer/", {}, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Create Volunteer")

    @patch("staff.views.volunteer_management.reset_password")
    def test_valid_post_request(self, mock):
        arg = {
            "username": "username",
            "first_name": "first_name",
            "last_name": "last_name",
            "email": "mow.charlottesville@gmail.com",
            "join_date": datetime.date.today(),
            "address": "None",
        }
        res = self.client.post("/staff/create-volunteer/", arg, follow=True)
        self.assertRedirects(res, "/staff/manage-volunteers/")
        Volunteer.objects.get(
            user__username="username",
            user__email="mow.charlottesville@gmail.com")
        mock.assert_called()
