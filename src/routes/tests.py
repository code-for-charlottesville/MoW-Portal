import datetime
from unittest.mock import patch

from django.test import Client, TestCase
from freezegun import freeze_time

import interfaces.address_lookup
from meals.constants import MOW_LAT, MOW_LON, ROUTE_TYPE_NAME
from models.models import Customer, JobType, Route, User
from routes import utility
from routes.forms import AddCustomerForm, RouteFormNoType

from . import views

# Create your tests here.


@patch("interfaces.address_lookup.validate",
       lambda *a, **k: {"lat": None, "lng": None})
class TestRoutes(TestCase):
    def setUp(self):
        client = Client()
        route_type, _ = JobType.objects.get_or_create(name=ROUTE_TYPE_NAME)
        Route.objects.get_or_create(
            name="TEST ROUTE", job_type=route_type, number=1)
        self.client.force_login(
            User.objects.get_or_create(
                username="admin",
                password="pass@123",
                email="admin@admin.com",
                is_staff=True,
            )[0])

    def test_routes_path(self):
        """ This tests if you can access the route page """
        __author__ = "Alex Hicks"
        response = self.client.get("/routes/1/")
        self.assertEqual(response.status_code, 200)

    def test_routes_path_wrong(self):
        """ This verifies that the volunteer page is not the route page """
        __author__ = "Alex Hicks"
        response = self.client.get("/volunteer/1/")
        self.assertEqual(response.status_code, 404)

    def test_routes_has_route_auto(self):
        """ This verifies there is no auto route """
        __author__ = "Alex Hicks"
        response = self.client.get("/routes/auto/")
        self.assertEqual(response.status_code, 404)

    def test_routes_has_route_default(self):
        """ This verifies there is no default route page """
        __author__ = "Alex Hicks"
        response = self.client.get("/routes/")
        self.assertEqual(response.status_code, 404)

    def test_routes_path_invalid(self):
        """ This verifies there are no negative routes """
        __author__ = "Alex Hicks"
        response = self.client.get("/routes/-1/")
        self.assertEqual(response.status_code, 404)

    def test_routes_path_0_invalid(self):
        """ This verifies there is no route 0 """
        __author__ = "Alex Hicks"
        response = self.client.get("/routes/0/")
        self.assertEqual(response.status_code, 404)

    def test_routes_path_arbitrary_large_invalid(self):
        """ This verifies there are not 10000 routes """
        __author__ = "Alex Hicks"
        response = self.client.get("/routes/10000/")
        self.assertEqual(response.status_code, 404)

    def test_routes_path_arbitrary_small_invalid(self):
        """ This verifies there are not negative large routes """
        __author__ = "Alex Hicks"
        response = self.client.get("/routes/-10000/")
        self.assertEqual(response.status_code, 404)

    def test_incorrect_app_name(self):
        """ This verifies that the app name is routes not route """
        __author__ = "Alex Hicks"
        response = self.client.get("/route/1")
        self.assertEqual(response.status_code, 404)


@patch("interfaces.address_lookup.validate",
       lambda *a, **k: {"lat": None, "lng": None})
class TestCreateRoutes(TestCase):
    @patch("interfaces.address_lookup.validate",
           lambda *a, **k: {"lat": None, "lng": None})
    def setUp(self):
        job_type = JobType.objects.create(name="Route")
        self.route = Route.objects.create(
            number=1, name="Route 1", num_vols_required=1, job_type=job_type
        )
        self.route1 = Route.objects.create(
            number=2, name="Route 2", num_vols_required=1, job_type=job_type
        )
        self.c1 = Customer.objects.create(
            first_name="name", route=self.route, address="")

    def test_route_customers(self):
        """ This verifies the customer order """
        __author__ = "Alex Hicks"
        self.assertEqual([self.c1.pk], list(self.route.get_customer_order()))

    def test_change_route(self):
        """ This edits and tests the customer order """
        __author__ = "Alex Hicks"
        self.route = Route.objects.get(number=2)
        self.assertEqual([], list(self.route1.get_customer_order()))


@freeze_time("2020-03-13")
@patch("interfaces.address_lookup.validate",
       lambda *a, **k: {"lat": None, "lng": None})
class TestMoveCustomer(TestCase):
    @patch("interfaces.address_lookup.validate",
           lambda *a, **k: {"lat": None, "lng": None})
    def setUp(self):
        job_type = JobType.objects.create(name="Route")
        self.route = Route.objects.create(
            number=1, name="Route 1", num_vols_required=1, job_type=job_type
        )
        self.c1 = Customer.objects.create(
            first_name="test",
            last_name="customer1",
            address={"raw": "100 street"},
            birth_date="1999-01-01",
            phone="7035555555",
            route=self.route,
        )
        self.c2 = Customer.objects.create(
            first_name="test",
            last_name="customer",
            address={"raw": "100 street"},
            birth_date="1999-01-01",
            phone="7035555555",
            route=self.route,
        )
        self.route.set_customer_order([self.c1.pk, self.c2.pk])
        self.client = Client()
        self.day = datetime.date.today().strftime("%m-%d-%Y")
        self.client.force_login(
            User.objects.get_or_create(
                username="admin",
                password="pass@123",
                email="admin@admin.com",
                is_staff=True,
            )[0])

    def test_move_up_normal(self):
        """
        move up as expected
        """
        __author__ = "Kyle-L45"
        response = self.client.get(
            f"/routes/move-customer/{self.route.number}/1/up/", follow=True
        )
        customer_order = list(self.route.get_customer_order())
        self.assertEqual(customer_order, [self.c2.pk, self.c1.pk])
        self.assertRedirects(response, f"/routes/{self.route.number}/")

    def test_move_down_normal(self):
        """
        move down as expected
        """
        __author__ = "Kyle-L45"
        response = self.client.get(
            f"/routes/move-customer/{self.route.number}/0/down/", follow=True
        )
        customer_order = list(self.route.get_customer_order())
        self.assertEqual(customer_order, [self.c2.pk, self.c1.pk])
        self.assertRedirects(response, f"/routes/{self.route.number}/")

    def test_move_up_0_index(self):
        """
        requesting move up as a zero index should have no effect
        """
        __author__ = "Kyle-L45"
        response = self.client.get(
            f"/routes/move-customer/{self.route.number}/0/up/", follow=True
        )
        customer_order = list(self.route.get_customer_order())
        self.assertEqual(customer_order, [self.c1.pk, self.c2.pk])
        self.assertRedirects(response, f"/routes/{self.route.number}/")

    def test_move_down_last_index(self):
        """
        requesting move up as a zero index should have no effect
        """
        __author__ = "Kyle-L45"
        response = self.client.get(
            f"/routes/move-customer/{self.route.number}/1/down/", follow=True
        )
        customer_order = list(self.route.get_customer_order())
        self.assertEqual(customer_order, [self.c1.pk, self.c2.pk])
        self.assertRedirects(response, f"/routes/{self.route.number}/")

    def test_move_up_index_out_of_bounds(self):
        """
        should just leave the list order as is
        """
        __author__ = "Kyle-L45"
        response = self.client.get(
            f"/routes/move-customer/{self.route.number}/3/down/", follow=True
        )
        customer_order = list(self.route.get_customer_order())
        self.assertEqual(customer_order, [self.c1.pk, self.c2.pk])
        self.assertRedirects(response, f"/routes/{self.route.number}/")

    def test_route_does_not_exist(self):
        """
        should get caught and redirect
        """
        __author__ = "Kyle-L45"
        response = self.client.get(
            "/routes/move-customer/0/1/up/", follow=True)
        self.assertEqual(response.status_code, 404)

    def test_direction_not_up_or_down(self):
        """
        should leave the order as is
        """
        __author__ = "Kyle-L45"
        response = self.client.get(
            f"/routes/move-customer/{self.route.number}/1/left/", follow=True
        )
        customer_order = list(self.route.get_customer_order())
        self.assertEqual(customer_order, [self.c1.pk, self.c2.pk])
        self.assertRedirects(response, f"/routes/{self.route.number}/")

    def test_no_customers_on_route(self):
        """
        should just leave the list order as is
        """
        __author__ = "Kyle-L45"
        self.c1.delete()
        self.c2.delete()
        response = self.client.get(
            f"/routes/move-customer/{self.route.number}/0/down/", follow=True
        )
        customer_order = list(self.route.get_customer_order())
        self.assertEqual(customer_order, [])
        self.assertRedirects(response, f"/routes/{self.route.number}/")


@freeze_time("2020-03-13")
@patch("interfaces.address_lookup.validate",
       lambda *a, **k: {"lat": None, "lng": None})
class TestRemoveCustomer(TestCase):
    @patch("interfaces.address_lookup.validate",
           lambda *a, **k: {"lat": None, "lng": None})
    def setUp(self):
        job_type = JobType.objects.create(name="Route")
        self.route = Route.objects.create(
            number=1, name="Route 1", num_vols_required=1, job_type=job_type
        )
        self.c1 = Customer.objects.create(
            first_name="test",
            last_name="customer1",
            address={"raw": "704 Rose Hill Drive, Charlottesville, VA 22903"},
            birth_date="1999-01-01",
            phone="7035555555",
            route=self.route,
        )
        self.c2 = Customer.objects.create(
            first_name="test",
            last_name="customer",
            address={"raw": "704 Rose Hill Drive, Charlottesville, VA 22903"},
            birth_date="1999-01-01",
            phone="7035555555",
            route=self.route,
        )
        self.c3 = Customer.objects.create(
            first_name="test1",
            last_name="customer1",
            address={"raw": "Not a real place"},
            birth_date="1999-01-01",
            phone="7035555555",
            route=self.route,
        )
        self.c4 = Customer.objects.create(
            first_name="test12",
            last_name="customer1",
            address={"raw": "Not a real place"},
            birth_date="1999-01-01",
            phone="7035555555",
            route=None,
        )
        self.route.set_customer_order([self.c1.pk, self.c2.pk])
        self.client = Client()
        self.day = datetime.date.today().strftime("%m-%d-%Y")
        self.post_dict = {
            "route": self.route.number,
            "direction": None,
            "index": None}
        self.client.force_login(
            User.objects.get_or_create(
                username="admin",
                password="pass@123",
                email="admin@admin.com",
                is_staff=True,
            )[0])

    def test_save_upon_removal(self):
        """ This test ensures that the historical_route field is set
        when a customer is removed from their route """
        __author__ = "Nate Strawser"
        self.assertEqual(self.c1.historical_route, "")
        utility.remove_customer_from_route(self.c1)
        self.assertEqual(self.c1.historical_route, str(self.route))

    def test_remove_from_none_route(self):
        """ This test make sure that removing from a none route does not update historical route """
        __author__ = "Alex Hicks"
        self.assertEqual(self.c4.historical_route, "")
        utility.remove_customer_from_route(self.c4)
        self.assertEqual(self.c4.historical_route, "")

    def test_reset_historical_route_on_route_save(self):
        """ This test ensures that the historical_route field is set
        to the empty string when a customer is added to a new route """
        __author__ = "Nate Strawser"
        self.assertEqual(self.c1.historical_route, "")
        utility.remove_customer_from_route(self.c1)
        self.assertEqual(self.c1.historical_route, str(self.route))
        utility.add_customer_to_route(self.c1, self.route)
        self.assertEqual(self.c1.historical_route, "")

    def test_historical_route_displays_on_form(self):
        """ This test ensures the historical_route field displays on
        the edit customer page """
        __author__ = "Nate Strawser"
        response = self.client.get(f"/staff/edit-customer/{self.c1.pk}/")
        self.assertContains(response, "Historical route")


class TestLatLon(TestCase):
    @patch("interfaces.address_lookup.validate", lambda *a,
           **k: {"lat": MOW_LAT, "lng": MOW_LON})
    def test_view_route_on_day(self):
        job_type = JobType.objects.create(name="Route")
        self.route = Route.objects.create(
            number=1, name="Route 1", num_vols_required=1, job_type=job_type
        )
        self.c1 = Customer.objects.create(
            first_name="test",
            last_name="customer1",
            address={"raw": "704 Rose Hill Drive, Charlottesville, VA 22903"},
            birth_date="1999-01-01",
            phone="7035555555",
            route=self.route,
        )
        self.c2 = Customer.objects.create(
            first_name="test",
            last_name="customer",
            address={
                "raw": "107 Piedmont Avenue North, Charlottesville, VA 22903"},
            birth_date="1999-01-01",
            phone="7035555555",
            route=self.route,
        )
        self.c3 = Customer.objects.create(
            first_name="test1",
            last_name="customer1",
            address={"raw": "not a real place"},
            birth_date="1999-01-01",
            phone="7035555555",
            route=self.route,
        )
        self.route.set_customer_order([self.c1.pk, self.c2.pk])
        self.client = Client()
        self.day = datetime.date.today().strftime("%m-%d-%Y")
        self.post_dict = {
            "route": self.route.number,
            "direction": None,
            "index": None}
        self.client.force_login(
            User.objects.get_or_create(
                username="admin",
                password="pass@123",
                email="admin@admin.com",
                is_staff=True,
            )[0])
        """ This tests to make sure the view route on day view is not alive yet """
        __author__ = "Alex Hicks"
        response = self.client.get(f"/routes/1/02-26-2020/")
        self.assertEqual(response.status_code, 200)

    def test_lat_field_after_validate(self):
        """ This tests that the lat field was correctly added to the model """
        __author__ = "Michael Benos"
        job_type = JobType.objects.create(name="Route")
        self.route = Route.objects.create(
            number=1, name="Route 1", num_vols_required=1, job_type=job_type
        )
        self.c2 = Customer.objects.create(
            first_name="test",
            last_name="customer",
            address={
                "raw": "107 Piedmont Avenue North, Charlottesville, VA 22903"},
            birth_date="1999-01-01",
            phone="7035555555",
            route=self.route,
        )
        self.route.set_customer_order([self.c2.pk])
        self.client = Client()
        self.day = datetime.date.today().strftime("%m-%d-%Y")
        self.post_dict = {
            "route": self.route.number,
            "direction": None,
            "index": None}
        self.client.force_login(
            User.objects.get_or_create(
                username="admin",
                password="pass@123",
                email="admin@admin.com",
                is_staff=True,
            )[0])
        geom = interfaces.address_lookup.validate(self.c2.address)
        self.c2.lat = geom["lat"]
        self.assertAlmostEqual(self.c2.lat, 38.03774, places=3)
        self.c2.lon = geom["lng"]
        self.assertAlmostEqual(self.c2.lon, -78.48749, places=3)

    def test_validate_failure_lat(self):
        """ This tests that the lat field was correctly added to the model """
        __author__ = "Michael Benos"
        job_type = JobType.objects.create(name="Route")
        self.route = Route.objects.create(
            number=1, name="Route 1", num_vols_required=1, job_type=job_type
        )
        self.c3 = Customer.objects.create(
            first_name="test1",
            last_name="customer1",
            address={"raw": "not a real place"},
            birth_date="1999-01-01",
            phone="7035555555",
            route=self.route,
        )
        self.route.set_customer_order([self.c3.pk])
        self.client = Client()
        self.day = datetime.date.today().strftime("%m-%d-%Y")
        self.post_dict = {
            "route": self.route.number,
            "direction": None,
            "index": None}
        self.client.force_login(
            User.objects.get_or_create(
                username="admin",
                password="pass@123",
                email="admin@admin.com",
                is_staff=True,
            )[0])
        geom = interfaces.address_lookup.validate(self.c3.address)
        self.c3.lat = geom["lat"]
        self.assertAlmostEqual(self.c3.lat, MOW_LAT, places=3)
        self.c3.lon = geom["lng"]
        self.assertAlmostEqual(self.c3.lon, MOW_LON, places=3)


@patch("interfaces.address_lookup.validate",
       lambda *a, **k: {"lat": None, "lng": None})
class TestForms(TestCase):
    @patch("interfaces.address_lookup.validate",
           lambda *a, **k: {"lat": None, "lng": None})
    def setUp(self):
        job_type = JobType.objects.create(name="Route")
        self.route = Route.objects.create(
            number=1, name="Route 1", num_vols_required=1, job_type=job_type
        )
        self.route1 = Route.objects.create(
            number=2, name="Route 2", num_vols_required=1, job_type=job_type
        )
        self.route2 = Route.objects.create(
            number=3, name="Route 3", num_vols_required=1, job_type=job_type
        )
        self.c1 = Customer.objects.create(
            first_name="test",
            last_name="customer1",
            address={"raw": "704 Rose Hill Drive, Charlottesville, VA 22903"},
            birth_date="1999-01-01",
            phone="7035555555",
            route=self.route1,
        )
        self.c3 = Customer.objects.create(
            first_name="test12",
            last_name="customer1",
            address={"raw": "704 Rose Hill Drive, Charlottesville, VA 22903"},
            birth_date="1999-01-01",
            phone="7035555555",
            route=None,
        )
        self.c2 = Customer.objects.create(
            first_name="test1",
            last_name="customer1",
            address={"raw": "704 Rose Hill Drive, Charlottesville, VA 22903"},
            birth_date="1999-01-01",
            phone="7035555555",
            route=self.route,
        )
        self.client = Client()
        self.route.set_customer_order([self.c1.pk, self.c2.pk])
        self.day = datetime.date.today().strftime("%m-%d-%Y")
        self.client.force_login(
            User.objects.get_or_create(
                username="admin",
                password="pass@123",
                email="admin@admin.com",
                is_staff=True,
            )[0])

    def test_add_customer_form_already_in_route(self):
        """ This tests the add_customer_form for a customer that is already on the route """
        __author__ = "Alex Hicks"
        form = AddCustomerForm(
            data={
                "route": self.route,
                "customer": self.c2.pk})
        valid = form.is_valid()
        self.assertFalse(valid)

    def test_add_customer_form_on_another_route(self):
        """ This tests the add_customer_form for a customer that is already on another route """
        __author__ = "Alex Hicks"
        form = AddCustomerForm(
            data={
                "route": self.route1,
                "customer": self.c2.pk})
        valid = form.is_valid()
        self.assertFalse(valid)

    def test_add_customer_form_add_customer(self):
        """ This tests the add_customer_form for a customer that is not already on another route """
        __author__ = "Alex Hicks"
        form = AddCustomerForm(
            data={
                "route": self.route2,
                "customer": self.c3.pk})
        valid = form.is_valid()
        self.assertTrue(valid)

    def test_add_customer_form_in_view(self):
        """ This tests the add_customer_form in the view it is used in """
        __author__ = "Alex Hicks"
        form = AddCustomerForm(
            data={
                "route": self.route2,
                "customer": self.c3.pk})
        data = {
            "route": self.route2,
            "customer": self.c3.pk,
            "add_customer_form": form}
        response = self.client.post(
            f"/routes/{self.route2.number}/", data, follow=True)
        self.assertEqual(response.status_code, 200)
        # response = self.client.post(f"/routes/{self.route2.number}/", data)
        # self.assertRedirects(response, f"/routes/{self.route2.number}/")

    def test_route_form_is_valid(self):
        """ This tests whether the route form sent is valid """
        __author__ = "Alex Hicks"
        data = {"name": "test13", "num_vols_required": 1, "number": 50}
        form = RouteFormNoType(data=data)
        valid = form.is_valid()
        self.assertTrue(valid)

    def test_route_form_no_type(self):
        """ This tests the RouteFormNoType in the view it is used in """
        __author__ = "Alex Hicks"
        data = {"name": "test13", "num_vols_required": 1, "number": 3}
        response = self.client.post(f"/routes/{self.route2.number}/", data)
        self.assertRedirects(response, f"/routes/{self.route2.number}/")


@patch("interfaces.address_lookup.validate",
       lambda *a, **k: {"lat": None, "lng": None})
class TestViewRouteOnDay(TestCase):
    @patch("interfaces.address_lookup.validate",
           lambda *a, **k: {"lat": None, "lng": None})
    def setUp(self):
        job_type = JobType.objects.create(name="Route")
        self.route = Route.objects.create(
            number=1, name="Route 1", num_vols_required=1, job_type=job_type
        )
        self.c1 = Customer.objects.create(
            first_name="test",
            last_name="customer1",
            address={"raw": "704 Rose Hill Drive, Charlottesville, VA 22903"},
            birth_date="1999-01-01",
            phone="7035555555",
            route=self.route,
        )
        self.client = Client()
        self.route.set_customer_order([self.c1.pk])
        self.day = datetime.date.today().strftime("%m-%d-%Y")

    def test_date_format_staff(self):
        """ This checks that a bad date format as a staff user redirects correctly """
        __author__ = "Alex Hicks"
        self.client.force_login(
            User.objects.get_or_create(
                username="admin",
                password="pass@123",
                email="admin@admin.com",
                is_staff=True,
            )[0])
        response = self.client.get(f"/routes/1/{4}/")
        self.assertRedirects(response, f"/routes/{self.route.number}/")

    def test_date_format_volunteer(self):
        """ This checks that a bad date format as a volunteer errors correctly """
        __author__ = "Alex Hicks"
        self.client.force_login(
            User.objects.get_or_create(
                username="admin",
                password="pass@123",
                email="admin@admin.com",
                is_staff=False,
            )[0])
        response = self.client.get(f"/routes/1/{4}/")
        self.assertEqual(response.status_code, 404)


@patch("interfaces.address_lookup.validate",
       lambda *a, **k: {"lat": None, "lng": None})
class TestCustomerManagement(TestCase):
    @patch("interfaces.address_lookup.validate",
           lambda *a, **k: {"lat": None, "lng": None})
    def setUp(self):
        job_type = JobType.objects.create(name="Route")
        self.route = Route.objects.create(
            number=1, name="Route 1", num_vols_required=1, job_type=job_type
        )
        self.route1 = Route.objects.create(
            number=2, name="Route 2", num_vols_required=1, job_type=job_type
        )
        self.c1 = Customer.objects.create(
            first_name="test",
            last_name="customer1",
            address={"raw": "704 Rose Hill Drive, Charlottesville, VA 22903"},
            birth_date="1999-01-01",
            phone="7035555555",
            route=self.route,
        )
        self.client = Client()
        self.day = datetime.date.today()
        self.route.set_customer_order([self.c1.pk])
        self.client.force_login(
            User.objects.get_or_create(
                username="admin",
                password="pass@123",
                email="admin@admin.com",
                is_staff=True,
            )[0])

    def test_remove_customer(self):
        """ This verifies that removing a customer redirects correctly """
        __author__ = "Alex Hicks"
        response = self.client.post(
            f"/routes/remove-customer/{self.route.number}/{self.c1.pk}/"
        )
        self.assertRedirects(response, f"/routes/{self.route.number}/")

    def test_add_and_remove_customer(self):
        """ This verifies that removing and adding a customer to a new route redirects correctly """
        __author__ = "Alex Hicks"
        response = self.client.post(
            f"/routes/add-and-remove-customer/{self.c1.pk}/{self.route1.number}/"
        )
        self.assertRedirects(response, f"/routes/{self.route1.number}/")

    def test_parse_date_form_good(self):
        """ This verifies that with a valid date, parse_date_form redirects correctly """
        __author__ = "Alex Hicks"
        data = {"date": self.day}
        response = self.client.post(
            f"/routes/parse-date-form/{self.route.number}/", data)
        self.assertRedirects(
            response,
            f"/routes/{self.route.number}/{self.day.strftime('%m-%d-%Y')}/")

    def test_parse_date_form_bad(self):
        """ This verifies that with a bad date, parse_date_form redirects correctly """
        __author__ = "Alex Hicks"
        data = {"date": 3}
        response = self.client.post(
            f"/routes/parse-date-form/{self.route.number}/", data)
        self.assertRedirects(
            response,
            f"/routes/{self.route.number}/{self.day.strftime('%m-%d-%Y')}/")
