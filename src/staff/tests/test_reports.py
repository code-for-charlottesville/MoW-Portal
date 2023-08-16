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


class TestJoinDateReport(TestCase):
    def setUp(self):
        client = Client()
        self.client.force_login(
            User.objects.get_or_create(
                username="admin",
                password="pass@123",
                email="admin@admin.com",
                is_staff=True,
            )[0])

    def test_view(self):
        """ This test ensures the join date report is up."""
        __author__ = "Nate Strawser"
        day = datetime.date.today()
        response = self.client.get("/pdfs/volunteer-join-date-report")
        self.assertEqual(response.status_code, 200)

    def test_wrong_view(self):
        """ This ensures you can't access the report through the /staff/ prefix"""
        __author__ = "Nate Strawser"
        day = datetime.date.today()
        response = self.client.get("/staff/volunteer-join-date-report")
        self.assertEqual(response.status_code, 302)
