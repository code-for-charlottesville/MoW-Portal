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


class TestManageCustomers(TestCase):
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

        self.customer = Customer.objects.create(
            first_name="test",
            last_name="customer",
            address="100 street",
            birth_date="1999-01-01",
            phone="7035555555",
        )

    def test_correct_path(self):
        __author__ = "Kevin Naddoni"
        response = self.client.post("/staff/manage-customers/",)
        self.assertEqual(response.status_code, 200)

    def test_authorization(self):
        __author__ = "Kevin Naddoni"
        self.client.logout()
        response = self.client.get("/staff/manage-customers/")
        self.assertEqual(response.status_code, 302)

    def test_table_rendering(self):
        __author__ = "Kevin Naddoni"
        response = self.client.get("/staff/manage-customers/")
        self.assertContains(response, "<tr>")

    def test_table_rendering_data(self):
        __author__ = "Kevin Naddoni"
        response = self.client.get("/staff/manage-customers/")
        self.assertTrue(b"test customer" in response.content)

    def test_table_rendering_after_deletion(self):
        __author__ = "Kevin Naddoni"
        self.customer.delete()
        response = self.client.get("/staff/manage-customers/")
        self.assertFalse(b"test customer" in response.content)


@patch("interfaces.address_lookup.validate",
       lambda *a, **k: {"lat": None, "lng": None})
class TestCustomerCreate(TestCase):
    def setUp(self):
        """ This setup logs the client in as a staff member. This is needed due to @staff_member_required decorator in customer_create()"""
        client = Client()
        self.client.force_login(
            User.objects.get_or_create(
                username="admin",
                password="pass@123",
                email="admin@admin.com",
                is_staff=True,
            )[0])

    def test_get_request(self):
        res = self.client.get("/staff/create-customer/")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Create Customer")

    def test_customer_create_success(self):
        """Test successful customer create"""

        response = self.client.post(
            "/staff/create-customer/",
            dict(
                route="",
                join_date="1999-12-11",
                pays="",
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
                diet="",
                cold_diet_restrictions="no",
                hot_diet_restrictions="no",
                num_weekend_meals=0,
                pet="",
                petfood="",
                end_date="2019-04-04",
                end_reason="none",
                referred="no",
                ref_phone="5555555555",
                bill_to="nobody",
                notes="no notes",
                meal_recurrence="RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE",
            ),
        )
        cust = Customer.objects.get(
            route=None,
            join_date=datetime.date(year=1999, month=12, day=11),
            pays=None,
            active=True,
            first_name="test",
            last_name="customer",
            phone="5555555555",
            printed_notes="no notes",
            birth_date=datetime.date(year=1997, month=12, day=12),
            sex="M",
            contact="5555555555",
            contact_phone="5555555555",
            diet=None,
            cold_diet_restrictions="no",
            hot_diet_restrictions="no",
            pet=None,
            petfood=None,
            end_date=datetime.date(year=2019, month=4, day=4),
            end_reason="none",
            referred="no",
            ref_phone="5555555555",
            bill_to="nobody",
            notes="no notes",
            meal_recurrence="RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE",
        )
        self.assertIn("555 Main St.", str(cust.address))
        self.assertEqual(response.status_code, 302)


class TestCustomerCreateFailure(TestCase):
    def setUp(self):
        client = Client()
        self.client.force_login(
            User.objects.get_or_create(
                username="admin",
                password="pass@123",
                email="admin@admin.com",
                is_staff=True,
            )[0])

    def test_wrong_path(self):
        response = self.client.post("/staff/create/",)
        self.assertEqual(response.status_code, 404)

    def test_empty_data(self):
        response = self.client.post("/staff/create-customer/", {})
        self.assertFormError(
            response,
            "form",
            "first_name",
            "This field is required.")


class TestDeleteCustomer(TestCase):
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
        self.customer = Customer.objects.create(
            route=None,
            join_date="1999-12-11",
            pays=None,
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
            num_weekend_meals=0,
            pet=None,
            petfood=None,
            end_date="2019-04-04",
            end_reason="none",
            referred="no",
            ref_phone="5555555555",
            bill_to="nobody",
            notes="no notes",
            meal_recurrence="RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE",
        )

    def test_delete_404(self):
        res = self.client.get("/staff/delete-customer/0/")
        self.assertEqual(res.status_code, 404)

    def test_delete_success(self):
        pk = self.customer.pk
        res = self.client.get(f"/staff/delete-customer/{pk}/", follow=True)
        self.assertRedirects(res, "/staff/manage-customers/")
        with self.assertRaises(Customer.DoesNotExist):
            Customer.objects.get(pk=pk)


class TestEditCustomer(TestCase):
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
        self.customer = Customer.objects.create(
            route=None,
            join_date="1999-12-11",
            pays=None,
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
            num_weekend_meals=0,
            pet=None,
            petfood=None,
            end_date="2019-04-04",
            end_reason="none",
            referred="no",
            ref_phone="5555555555",
            bill_to="nobody",
            notes="no notes",
            meal_recurrence="RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE",
        )

    @patch("interfaces.address_lookup.validate",
           lambda *a, **k: {"lat": None, "lng": None})
    def test_invalid_form(self):
        res = self.client.post(
            f"/staff/edit-customer/{self.customer.pk}/",
            {},
            follow=True)
        self.assertContains(res, "Edit Customer")
        self.assertEqual(res.status_code, 200)

    @patch("interfaces.address_lookup.validate",
           lambda *a, **k: {"lat": None, "lng": None})
    def test_valid_edit(self):
        arg = dict(
            route="",
            join_date="1999-12-11",
            pays="",
            active=True,
            first_name="NEW FIRST NAME",
            last_name="NEW LAST NAME",
            address="555 Main St.",
            phone="5555555555",
            printed_notes="no notes",
            birth_date="1997-12-12",
            sex="M",
            contact="5555555555",
            contact_phone="5555555555",
            diet="",
            cold_diet_restrictions="no",
            hot_diet_restrictions="no",
            num_weekend_meals=0,
            pet="",
            petfood="",
            end_date="2019-04-04",
            end_reason="none",
            referred="no",
            ref_phone="5555555555",
            bill_to="nobody",
            notes="no notes",
            meal_recurrence="RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE",
        )
        res = self.client.post(
            f"/staff/edit-customer/{self.customer.pk}/",
            arg,
            follow=True)
        self.assertRedirects(res, "/staff/manage-customers/")
        Customer.objects.get(
            first_name="NEW FIRST NAME",
            last_name="NEW LAST NAME")
