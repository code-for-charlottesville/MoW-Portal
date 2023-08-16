from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from accounts.forms import LoginForm, SignUpForm
from models.models import Volunteer

from . import views


# Create your tests here.
class TestSignUp(TestCase):
    def setUp(self):
        client = Client()

    def test_first_signup(self):
        """Test the signup functionality of the registration page"""
        response = self.client.post(
            "/accounts/login/",
            first_name="test",
            last_name="user",
            username="testuser1",
            email="test@email.com",
            password1="correcthorsebatterystaple",
            password2="correcthorsebatterystaple",
        )
        self.assertEqual(response.status_code, 200)


class TestLogin(TestCase):
    def setUp(self):
        client = Client()
        User.objects.create(username="testlogin5678", password="okmijnuhb")

    def test_normal_login(self):
        self.client.login(username="testlogin5678", password="okmijnuhb")
        response = self.client.get("/accounts/login/")
        self.assertEqual(response.status_code, 200)

    def test_staff_login(self):
        # client may need to be further set up in
        self.client.login(username="admin", password="password")
        response = self.client.get("/accounts/login/")
        self.assertEqual(response.status_code, 200)

    # Login failure for an account that does not exist
    def test_nonexistent_login(self):
        self.client.login(username="nonexistent", password="nonexistent")
        response = self.client.get("/accounts/login/")
        # from selenium import webdriver
        # driver = webdriver.Chrome()
        # error_message = driver.find_elements_by_class_name("errorlist")
        # self.assertEqual(error_message[0].innerText, "Please enter a correct username and password. Note that both fields may be case-sensitive.")
        self.assertEqual(response.status_code, 200)


class TestForms(TestCase):
    def setUp(self):
        client = Client()
        User.objects.create(username="testlogin56789", password="okmijnuhb")
        User.objects.create(
            username="testlogin5678",
            password="okmijnuhb",
            is_active=True)

    def test_sign_up_form_good(self):
        data = {
            "first_name": "John",
            "last_name": "Smith",
            "username": "johnsmith",
            "email": "john@smith.com",
            "is_staff": True,
        }
        form = SignUpForm(data=data)
        valid = form.is_valid()
        self.assertTrue(valid)

    def test_sign_up_form_bad(self):
        data = {
            "first_name": "John",
            "last_name": "Smith",
            "username": "testlogin5678",
            "email": "john@smith.com",
            "is_staff": True,
        }
        form = SignUpForm(data=data)
        valid = form.is_valid()
        self.assertFalse(valid)

    # def test_login_form_good(self):
    #     data = {"username": "testlogin5678", "password": "okmijnuhb"}
    #     form = LoginForm(data=data)
    #     valid = form.is_valid()
    #     self.assertTrue(valid)

    def test_login_good_active(self):
        data = {"username": "testlogin5678", "password": "okmijnuhb"}
        response = self.client.post(f"/accounts/login/", data)
        self.assertEqual(response.status_code, 200)

    def test_login_good_inactive(self):
        data = {"username": "testlogin56789", "password": "okmijnuhb"}
        response = self.client.post(f"/accounts/login/", data)
        self.assertEqual(response.status_code, 200)

    def test_login_bad(self):
        data = {"username": "testlogn5678", "password": "okmijnuhb"}
        response = self.client.post(f"/accounts/login/", data)
        self.assertEqual(response.status_code, 200)


class TestViews(TestCase):
    def setUp(self):
        client = Client()

    def test_home_staff(self):
        self.client.force_login(
            User.objects.get_or_create(
                username="admin",
                password="pass@123",
                email="admin@admin.com",
                is_staff=True,
            )[0])
        response = self.client.post(f"/")
        self.assertTemplateUsed("../staff/templates/home.html")
        self.assertRedirects(response, "/staff/")

    def test_home_vol(self):
        self.client.force_login(
            User.objects.get_or_create(
                username="admin",
                password="pass@123",
                email="admin@admin.com",
                is_staff=False,
            )[0])
        response = self.client.post(f"/")
        self.assertTemplateUsed("../staff/templates/home.html")
        self.assertRedirects(response, "/volunteer/")

    def test_home_no_login(self):
        response = self.client.post(f"/")
        self.assertTemplateUsed("../staff/templates/home.html")
        self.assertContains(response, "Welcome to the Meals on Wheels Portal")
