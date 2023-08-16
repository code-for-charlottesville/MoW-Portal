import json

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


class TestAutocompleter(TestCase):
    def setUp(self):
        client = Client()
        self.staffuser = User.objects.get_or_create(
            username="admin",
            password="pass@123",
            email="admin@admin.com",
            is_staff=True,
        )[0]
        self.staffvol = Volunteer.objects.get(user=self.staffuser)
        self.client.force_login(self.staffuser)
        self.user = User.objects.create(
            username="username",
            first_name="FirstName",
            last_name="LastName",
            email="emailaddress@domain.com",
        )
        self.vol = Volunteer.objects.get(user=self.user)

    def test_volunteer_empty_query(self):
        __author__ = "Maxwell Patek"
        response = self.client.get("/staff/volunteer-autocomplete/",)
        data = json.loads(response.content)
        self.assertIn(self.vol.id, [int(item["id"])
                                    for item in data["results"]])
        self.assertIn(self.staffvol.id,
                      [int(item["id"]) for item in data["results"]])

    def test_volunteer_query_match(self):
        __author__ = "Maxwell Patek"
        response = self.client.get(
            "/staff/volunteer-autocomplete/",
            dict(
                q="First Last"))
        data = json.loads(response.content)
        self.assertIn(self.vol.id, [int(item["id"])
                                    for item in data["results"]])
        self.assertNotIn(self.staffvol.id,
                         [int(item["id"]) for item in data["results"]])

    def test_volunteer_query_no_match(self):
        __author__ = "Maxwell Patek"
        response = self.client.get(
            "/staff/volunteer-autocomplete/",
            dict(
                q="First Lastt"))
        data = json.loads(response.content)
        self.assertNotIn(self.vol.id, [int(item["id"])
                                       for item in data["results"]])
        self.assertNotIn(self.staffvol.id,
                         [int(item["id"]) for item in data["results"]])
