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
    Diet,
    Job,
    JobType,
    ManagerAnnouncement,
    Payment,
    Pet,
    PetFood,
    Route,
    Substitution,
    Volunteer,
)
from staff import views


class TestOtherModels(TestCase):
    @patch("interfaces.address_lookup.validate",
           lambda *a, **k: {"lat": None, "lng": None})
    def setUp(self):
        client = Client()
        self.client.force_login(
            User.objects.get_or_create(
                username="admin",
                password="pass@123",
                email="admin@admin.com",
                is_staff=True,
            )[0])
        self.pet = Pet.objects.create(name="dog")
        self.pet_food = PetFood.objects.create(name="dog food")
        self.diet = Diet.objects.create(name="diet")
        self.payment = Payment.objects.create(name="payment")
        Customer.objects.create(
            pet=self.pet,
            petfood=self.pet_food,
            diet=self.diet,
            pays=self.payment,
            join_date=datetime.date.today(),
            active=True,
            first_name="name",
            last_name="name",
            address="1 First St.",
        )

    def test_delete_pet_404(self):
        res = self.client.get(f"/staff/delete-pet/{0}/")
        self.assertEqual(404, res.status_code)

    def test_delete_pet_food_404(self):
        res = self.client.get(f"/staff/delete-petfood/{0}/")
        self.assertEqual(404, res.status_code)

    def test_delete_payment_404(self):
        res = self.client.get(f"/staff/delete-payment/{0}/")
        self.assertEqual(404, res.status_code)

    def test_delete_diet_404(self):
        res = self.client.get(f"/staff/delete-diet/{0}/")
        self.assertEqual(404, res.status_code)

    def test_delete_pet_success(self):
        pk = self.pet.pk
        res = self.client.get(f"/staff/delete-pet/{pk}/")
        with self.assertRaises(Pet.DoesNotExist):
            Pet.objects.get(pk=pk)

    def test_delete_pet_food_success(self):
        pk = self.pet_food.pk
        res = self.client.get(f"/staff/delete-petfood/{pk}/")
        with self.assertRaises(PetFood.DoesNotExist):
            PetFood.objects.get(pk=pk)

    def test_delete_payment_success(self):
        pk = self.payment.pk
        res = self.client.get(f"/staff/delete-payment/{pk}/")
        with self.assertRaises(Payment.DoesNotExist):
            Payment.objects.get(pk=pk)

    def test_delete_diet_success(self):
        pk = self.diet.pk
        res = self.client.get(f"/staff/delete-diet/{pk}/")
        with self.assertRaises(Diet.DoesNotExist):
            Diet.objects.get(pk=pk)
