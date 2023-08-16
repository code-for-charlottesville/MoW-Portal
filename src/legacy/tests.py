from contextlib import redirect_stdout
from unittest import SkipTest
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from legacy.models import *
from meals.constants import (
    PACKER_COLD,
    PACKER_HOT,
    PACKER_TYPE_NAME,
    ROUTE_TYPE_NAME,
    SHUTTLE_TYPE_NAME,
    VOLS_PER_COLD,
    VOLS_PER_HOT,
)
from models.models import *

import datetime  # isort:skip


def silently_call_command(*args, **kwargs):
    with open("/dev/null", "w") as null:
        with redirect_stdout(null):
            call_command(*args, **kwargs)


class TestImportMethods(TestCase):
    def setUp(self):
        date_created = datetime.date(year=2020, month=1, day=10,)
        self.luser = LegacyUser.objects.create(
            username="username",
            email="user@email.com",
            is_superuser=False,
            is_staff=True,
            is_active=True,
            date_joined=date_created,
        )
        self.user = User.objects.create(
            username="username",
            email="user@email.com",
            is_superuser=False,
            is_staff=True,
            is_active=True,
            date_joined=date_created,
        )
        self.lvol = LegacyVolunteer.objects.create(
            user=self.luser, join_date=date_created,)
        self.vol = Volunteer.objects.get(user=self.user)
        self.vol.join_date = date_created
        self.vol.save()

    def test_easy_import_mixin(self):
        """
        __author__ = Maxwell Patek
        Using User as an test for EasyImportMixin,
        since its the most important usage of it
        """
        date_joined = datetime.datetime(year=2020, month=1, day=10,)
        user = LegacyUser.objects.create(
            password="password",
            last_login=None,
            is_superuser=False,
            username="username1",
            first_name="first",
            last_name="last",
            email="user@email.com",
            is_staff=False,
            is_active=True,
            date_joined=date_joined,
        )
        user._import()
        User.objects.get(
            password="password",
            last_login=None,
            is_superuser=False,
            username="username1",
            first_name="first",
            last_name="last",
            email="user@email.com",
            is_staff=False,
            is_active=True,
            date_joined=date_joined,
        )

    def test_route(self):
        """
        __author__ = Maxwell Patek
        """
        route_type, _ = JobType.objects.get_or_create(name=ROUTE_TYPE_NAME)
        rte = LegacyRoute.objects.create(
            route=10, calendarId="calid", description="description",
        )
        rte._import()
        Route.objects.get(
            name="Route 10",
            number=10,
            description="description",
            job_type=route_type,
        )

    def test_manager_announcement(self):
        """
        __author__ = Maxwell Patek
        """
        date_created = datetime.date(year=2020, month=1, day=10,)
        display_until = datetime.date(year=2030, month=10, day=10,)
        lma = LegacyManagerAnnouncement.objects.create(
            display_until=display_until,
            date_created=date_created,
            announcement="announcement",
            display=True,
            created_by=self.luser,
        )
        lma._import()
        ManagerAnnouncement.objects.get(
            display_until=display_until,
            date_created=date_created,
            announcement="announcement",
            created_by=Volunteer.objects.get(user=self.user),
        )

    def test_dont_send_entry(self):
        """
        __author__ = Maxwell Patek
        important to call refresh_from_db(), took a while to debug that...
        """
        ldse = LegacyDontsendentry.objects.create(
            to_address=self.user.email,
            when_added=datetime.datetime(year=2020, month=1, day=1),
        )
        ldse._import()
        self.vol.refresh_from_db()
        self.assertTrue(self.vol.dont_email)

    def test_packer_job(self):
        """
        __author__ = Maxwell Patek
        "Hot", "Cold", and "Supervisor" are the packer jobs in our current
        dump of the actual legacy db.
        Supervisor is being purposefully removed.
        """
        lpjs = [
            LegacyPackerjob.objects.create(name="Hot"),
            LegacyPackerjob.objects.create(name="Cold"),
            LegacyPackerjob.objects.create(name="Supervisor"),
        ]
        for lpj in lpjs:
            lpj._import()
        self.assertEqual(
            Job.objects.get(name=PACKER_HOT).num_vols_required, 1,
        )
        self.assertEqual(
            Job.objects.get(name=PACKER_COLD).num_vols_required, 1,
        )
        with self.assertRaises(Job.DoesNotExist):
            Job.objects.get(name__contains="Supervisor")

    @patch("legacy.models.split_recurrence")
    def test_volunteer_packer_job(self, mocked_split_recurrence):
        """
        __author__ = Maxwell Patek
        Verifies that
         1) assignments are created
         2) num_vols_required for the packer job is incremented accordingly

        Note: patching split_recurrence, is ok. There are seperate tests for that
        in interfaces.tests.test_recurrence. We want to isolate that fairly complex
        function from the test of the _import method itself.

        Warning: It's probably a bad idea to call other models' _import functions
        inside the test for this model. However, makes the test much simpler.
        """
        dom = DayOfMonth(2, 2)
        mocked_split_recurrence.return_value = [dom]
        lpj = LegacyPackerjob.objects.create(name="packer hot 1")
        pj = Job.objects.create(
            name=PACKER_HOT, job_type=JobType.objects.get_or_create(
                name=PACKER_TYPE_NAME)[0], )
        date_joined = datetime.datetime(year=2020, month=1, day=10,)
        other_user = LegacyUser.objects.create(
            password="password",
            last_login=None,
            is_superuser=False,
            username="username1",
            first_name="first",
            last_name="last",
            email="user@email.com",
            is_staff=False,
            is_active=True,
            date_joined=date_joined,
        )
        other_user._import()
        other_vol = LegacyVolunteer.objects.create(
            user=other_user, join_date=date_joined,)
        other_vol._import()

        lvpj1 = LegacyVolunteerpackerjob.objects.create(
            recurrences="", packer_job=lpj, volunteer=self.lvol,
        )
        lvpj2 = LegacyVolunteerpackerjob.objects.create(
            recurrences="", packer_job=lpj, volunteer=other_vol,
        )

        lvpj1._import()
        lvpj2._import()
        Assignment.objects.get(
            volunteer=self.vol,
            job=pj,
            day_of_week=dom.day_of_week,
            week_of_month=dom.week_of_month,
        )
        self.assertEqual(
            len(
                Assignment.objects.filter(
                    job=pj, day_of_week=dom.day_of_week, week_of_month=dom.week_of_month,
                )
            ),
            2,
        )
        pj.refresh_from_db()
        self.assertEqual(pj.num_vols_required, 2)

    @patch("interfaces.address_lookup.validate",
           lambda *a, **k: {"lat": None, "lng": None})
    def test_customer(self):
        """
        __author__ = Josh Santana
        """

        # foreign keyed objects necessary for customer init:
        date = datetime.datetime(year=2020, month=1, day=10,)
        l_diet = LegacyDiet.objects.create(name="diet", code="0")
        l_pays = LegacyPayment.objects.create(name="payment")
        l_route = LegacyRoute.objects.create(
            route=10, calendarId="calid", description="description"
        )
        l_pet = LegacyPet.objects.create(name="pet")
        l_petfood = LegacyPetFood.objects.create(name="petfood", code="0")

        l_diet._import()
        l_pays._import()
        l_route._import()
        l_pet._import()
        l_petfood._import()

        l_customer = LegacyCustomer.objects.create(
            route_order=0,
            join_date=date,
            active=True,
            first_name="Firstname",
            last_name="Lastname",
            address="123 Street",
            city="Charlottesvile",
            state="VA",
            zip="000000",
            phone="555-555-5555",
            printed_notes="notes",
            place_of_worship="church",
            birth_date=date,
            sex="F",
            contact="contact",
            contact_phone="555-555-5555",
            doctor="doctor",
            hospital="hospital",
            cold_diet_restrictions="cold restrictions",
            hot_diet_restrictions="hot restrictions",
            end_date=date,
            referred="referred",
            ref_phone="555-555-5555",
            agency="agency",
            in_care_of="caretaker",
            bill_to="bill",
            notes="notes",
            recurrences="",
            num_weekend_meals=0,
            location="location",
            diet=l_diet,
            pays=l_pays,
            route=l_route,
            death_date=date,
            pet=l_pet,
            petfood=l_petfood,
        )
        l_customer._import()
        Customer.objects.get(
            first_name="Firstname", last_name="Lastname",
        )

    def test_date_range(self):
        raise SkipTest

    def test_volunteer(self):

        # Sample date
        date_joined = datetime.datetime(year=2020, month=1, day=10,)

        # Create a legacy user
        l_user = LegacyUser.objects.create(
            username="username989",
            email="user@email.com",
            is_superuser=False,
            is_staff=True,
            is_active=True,
            date_joined=date_joined,
        )
        # Import it into new model
        l_user._import()

        # Create a legacy volunteer
        l_vol = LegacyVolunteer.objects.create(
            user=l_user,
            join_date=date_joined,
            first_name="test",
            last_name="vol",
            organization="test-org",
            home_phone="1231231234",
            cell_phone="1231231234",
            work_phone="1231231234",
            notes="notes",
            address="JPA",
            city="Charlottesville",
            state="VA",
        )

        # Import it into new model
        l_vol._import()

        # Fetch the imported user to use in the Volunteer query
        t = User.objects.get(username="username989",)

        # Check if it imported correctly
        new_vol = Volunteer.objects.get(
            user=t,
            join_date=date_joined,
            organization="test-org",
            home_phone="1231231234",
            cell_phone="1231231234",
            work_phone="1231231234",
            notes="notes",
        )

        # Testing data integrity on the imports
        self.assertEqual(new_vol.notes, l_vol.notes)

        # Testing import functionality with concatenating and model differences
        self.assertEqual(str(new_vol.address), "JPA, Charlottesville, VA")
        self.assertEqual(t.first_name, "test")

    def test_report_day(self):
        """very important, since our current dump has no report days.
        currently completely untested."""
        raise SkipTest

    def setUpSubs(self):
        """
        sets up users and volunteers for importing in substiutions
        cleans up code
        """
        date = datetime.date.today()
        # Create legacy users
        l_user_sub, _ = LegacyUser.objects.get_or_create(
            username="subvol",
            email="user@email.com",
            is_superuser=False,
            is_staff=True,
            is_active=True,
            date_joined=date,
        )
        l_user_assignment, _ = LegacyUser.objects.get_or_create(
            username="assignmentvol",
            email="user@email.com",
            is_superuser=False,
            is_staff=True,
            is_active=True,
            date_joined=date,
        )

        # Create legacy volunteers
        l_vol_sub, _ = LegacyVolunteer.objects.get_or_create(
            user=l_user_sub,
            join_date=date,
            first_name="test",
            last_name="vol",
            organization="test-org",
            home_phone="1231231234",
            cell_phone="1231231234",
            work_phone="1231231234",
            notes="notes",
            address="",
            city="Charlottesville",
            state="VA",
        )
        l_vol_assignment, _ = LegacyVolunteer.objects.get_or_create(
            user=l_user_assignment,
            join_date=date,
            first_name="test",
            last_name="vol",
            organization="test-org",
            home_phone="1231231234",
            cell_phone="1231231234",
            work_phone="1231231234",
            notes="notes",
            address="",
            city="Charlottesville",
            state="VA",
        )
        return l_user_sub, l_user_assignment, l_vol_sub, l_vol_assignment

    @patch("legacy.models.split_recurrence")
    def test_packer_job_substitution(self, mocked_split_recurrence):
        """
        __author__ = "Kyle-L45"
        """
        # user and volunteers
        l_user_sub, l_user_assignment, l_vol_sub, l_vol_assignment = self.setUpSubs()
        l_user_sub._import()
        l_user_assignment._import()
        l_vol_sub._import()
        l_vol_assignment._import()

        # create legacy packerjob
        l_packer_job, _ = LegacyPackerjob.objects.get_or_create(
            name=PACKER_HOT)
        l_packer_job._import()

        # setting up date
        date = datetime.date.today()
        dom = date_to_day_of_month(date)
        mocked_split_recurrence.return_value = [dom]

        # create legacy volunteerpackerjob
        l_vol_packer_job = LegacyVolunteerpackerjob(
            packer_job=l_packer_job, volunteer=l_vol_assignment, recurrences=""
        )
        l_vol_packer_job._import()

        # create legacy packer job substitution
        l_packer_sub = LegacyPackerjobsubstitution(
            date=date,
            requested_user=l_user_assignment,
            packer_job=l_packer_job,
            volunteer=l_vol_sub,
        )
        l_packer_sub._import()

        # setting up current model query
        sub_user = User.objects.get(username="subvol")
        sub_vol = Volunteer.objects.get(user=sub_user)
        assignment_user = User.objects.get(username="assignmentvol")
        assignment_vol = Volunteer.objects.get(user=assignment_user)
        assignment = Assignment.objects.get(
            job__name=PACKER_HOT,
            volunteer=assignment_vol,
            day_of_week=dom.day_of_week,
            week_of_month=dom.week_of_month,
        )

        # testing current model
        Substitution.objects.get(
            assignment=assignment,
            date=date,
            volunteer=sub_vol)

    @patch("legacy.models.split_recurrence")
    def test_packer_job_substitution_request(self, mocked_split_recurrence):
        """
        __author__ = Kyle-L45
        """
        # user and volunteers
        _, l_user_assignment, _, l_vol_assignment = self.setUpSubs()
        l_user_assignment._import()
        l_vol_assignment._import()

        # create legacy packer job
        l_packer_job, _ = LegacyPackerjob.objects.get_or_create(
            name=PACKER_HOT)
        l_packer_job._import()

        # setting up date
        date = datetime.date.today()
        dom = date_to_day_of_month(date)
        mocked_split_recurrence.return_value = [dom]

        # create legacy volunteerpackerjob
        l_vol_packer_job = LegacyVolunteerpackerjob(
            packer_job=l_packer_job, volunteer=l_vol_assignment, recurrences=""
        )
        l_vol_packer_job._import()

        # create legacy packer job substitution request
        l_packer_sub = LegacyPackerjobsubstitutionrequest(
            date=date, created_by=l_user_assignment, packer_job=l_packer_job
        )
        l_packer_sub._import()

        # setting up current model query
        assignment_user = User.objects.get(username="assignmentvol")
        assignment_vol = Volunteer.objects.get(user=assignment_user)
        assignment = Assignment.objects.get(
            job__name=PACKER_HOT,
            volunteer=assignment_vol,
            day_of_week=dom.day_of_week,
            week_of_month=dom.week_of_month,
        )

        # testing current model
        Substitution.objects.get(
            assignment=assignment,
            date=date,
            volunteer=None)

    def test_shuttle_route(self):
        """
        __author__ = Alex Hicks
        """
        l_shuttle_route, _ = LegacyShuttleroute.objects.get_or_create(
            name="shuttle one")
        l_shuttle_route._import()
        new_shuttle_route = Job.objects.get(name="shuttle one")

        # Testing if create in import works
        self.assertEqual(new_shuttle_route.num_vols_required, 1)
        # Testing if import in import works
        self.assertEqual(new_shuttle_route.name, l_shuttle_route.name)

    def test_volunteer_shuttle_route(self):
        """might want to patch split_recurrences, like in
        test_volunteer_packer_job"""
        raise SkipTest

    @patch("legacy.models.split_recurrence")
    def test_shuttle_route_substitution(self, mocked_split_recurrence):
        """
        __author__ = "Kyle-L45"
        """
        # user and volunteers
        l_user_sub, l_user_assignment, l_vol_sub, l_vol_assignment = self.setUpSubs()
        l_user_sub._import()
        l_user_assignment._import()
        l_vol_sub._import()
        l_vol_assignment._import()

        # create legacy shuttle route
        l_shuttle_route, _ = LegacyShuttleroute.objects.get_or_create(
            name="shuttle one")
        l_shuttle_route._import()

        # setting up date
        date = datetime.date.today()
        dom = date_to_day_of_month(date)
        mocked_split_recurrence.return_value = [dom]

        # create legacy volunteershuttleroute
        l_vol_shuttle_route = LegacyVolunteershuttleroute(
            shuttle_route=l_shuttle_route, volunteer=l_vol_assignment, recurrences="")
        l_vol_shuttle_route._import()

        # create shuttle route substitution
        l_shuttle_sub = LegacyShuttleroutesubstitution(
            date=date,
            requested_user=l_user_assignment,
            shuttle_route=l_shuttle_route,
            volunteer=l_vol_sub,
        )
        l_shuttle_sub._import()

        # setting up current model query
        sub_user = User.objects.get(username="subvol")
        sub_vol = Volunteer.objects.get(user=sub_user)
        assignment_user = User.objects.get(username="assignmentvol")
        assignment_vol = Volunteer.objects.get(user=assignment_user)
        assignment = Assignment.objects.get(
            job__name="shuttle one",
            volunteer=assignment_vol,
            day_of_week=dom.day_of_week,
            week_of_month=dom.week_of_month,
        )

        # testing current model
        Substitution.objects.get(
            assignment=assignment,
            date=date,
            volunteer=sub_vol)

    @patch("legacy.models.split_recurrence")
    def test_shuttle_route_substitution_request(self, mocked_split_recurrence):
        """
        __author__ = Kyle-L45
        """
        # user and volunteers
        _, l_user_assignment, _, l_vol_assignment = self.setUpSubs()
        l_user_assignment._import()
        l_vol_assignment._import()

        # create legacy shuttle route
        l_shuttle_route, _ = LegacyShuttleroute.objects.get_or_create(
            name="shuttle one")
        l_shuttle_route._import()

        # setting up date
        date = datetime.date.today()
        dom = date_to_day_of_month(date)
        mocked_split_recurrence.return_value = [dom]

        # create legacy volunteershuttleroute
        l_vol_shuttle_route = LegacyVolunteershuttleroute(
            shuttle_route=l_shuttle_route, volunteer=l_vol_assignment, recurrences="")
        l_vol_shuttle_route._import()

        # create shuttle route substitution request
        l_shuttle_sub = LegacyShuttleroutesubstitutionrequest(
            date=date, created_by=l_user_assignment, shuttle_route=l_shuttle_route)
        l_shuttle_sub._import()

        # setting up current model query
        assignment_user = User.objects.get(username="assignmentvol")
        assignment_vol = Volunteer.objects.get(user=assignment_user)
        assignment = Assignment.objects.get(
            job__name="shuttle one",
            volunteer=assignment_vol,
            day_of_week=dom.day_of_week,
            week_of_month=dom.week_of_month,
        )

        # testing current model
        Substitution.objects.get(
            assignment=assignment,
            date=date,
            volunteer=None)

    def test_volunteer_route(self):
        """might want to patch split_recurrences, like in
        test_volunteer_packer_job"""
        raise SkipTest

    @patch("legacy.models.split_recurrence")
    def test_substitution(self, mocked_split_recurrence):
        """
        __author__ = "Kyle-L45"
        """
        # user and volunteers
        l_user_sub, l_user_assignment, l_vol_sub, l_vol_assignment = self.setUpSubs()
        l_user_sub._import()
        l_user_assignment._import()
        l_vol_sub._import()
        l_vol_assignment._import()

        # create legacy route
        l_route, _ = LegacyRoute.objects.get_or_create(
            route=1, calendarId="", description="")
        l_route._import()

        # setting up date
        date = datetime.date.today()
        dom = date_to_day_of_month(date)
        mocked_split_recurrence.return_value = [dom]

        # create legacy volunteerroute
        l_volunteer_route = LegacyVolunteerroute(
            route=l_route, volunteer=l_vol_assignment, recurrences=""
        )
        l_volunteer_route._import()

        # create substitution
        l_sub = LegacySubstitution(
            date=date,
            requested_user=l_user_assignment,
            route=l_route,
            volunteer=l_vol_sub)
        l_sub._import()

        # setting up current model query
        sub_user = User.objects.get(username="subvol")
        sub_vol = Volunteer.objects.get(user=sub_user)
        assignment_user = User.objects.get(username="assignmentvol")
        assignment_vol = Volunteer.objects.get(user=assignment_user)
        job = Route.objects.get(number=1)
        assignment = Assignment.objects.get(
            job=job,
            volunteer=assignment_vol,
            day_of_week=dom.day_of_week,
            week_of_month=dom.week_of_month,
        )

        # testing current model
        Substitution.objects.get(
            assignment=assignment,
            date=date,
            volunteer=sub_vol)

    @patch("legacy.models.split_recurrence")
    def test_substitution_request(self, mocked_split_recurrence):
        """
        __author__ = "Kyle-L45"
        """
        # user and volunteers
        _, l_user_assignment, _, l_vol_assignment = self.setUpSubs()
        l_user_assignment._import()
        l_vol_assignment._import()

        # create legacy route
        l_route, _ = LegacyRoute.objects.get_or_create(
            route=1, calendarId="", description="")
        l_route._import()

        # setting up date
        date = datetime.date.today()
        dom = date_to_day_of_month(date)
        mocked_split_recurrence.return_value = [dom]

        # create legacy volunteerroute
        l_volunteer_route = LegacyVolunteerroute(
            route=l_route, volunteer=l_vol_assignment, recurrences=""
        )
        l_volunteer_route._import()

        # create substitution request
        l_sub = LegacySubstitutionrequest(
            date=date, created_by=l_user_assignment, route=l_route
        )
        l_sub._import()

        # setting up current model query
        assignment_user = User.objects.get(username="assignmentvol")
        assignment_vol = Volunteer.objects.get(user=assignment_user)
        job = Route.objects.get(number=1)
        assignment = Assignment.objects.get(
            job=job,
            volunteer=assignment_vol,
            day_of_week=dom.day_of_week,
            week_of_month=dom.week_of_month,
        )

        # testing current model
        Substitution.objects.get(
            assignment=assignment,
            date=date,
            volunteer=None)


class TestImportLegacyCommand(TestCase):
    __author__ = "Maxwell Patek"

    @patch("legacy.models.LegacyDiet._import")
    def test_no_objects(self, mocked_import):
        silently_call_command("importlegacy")
        mocked_import.assert_not_called()

    @patch("legacy.models.LegacyDiet._import")
    def test_one_instance(self, mocked_import):
        LegacyDiet.objects.create(name="diet", code="DIET")
        silently_call_command("importlegacy")
        mocked_import.assert_called()

    @patch("legacy.models.LegacyDiet._import")
    def test_multiple_instances(self, mocked_import):
        diets = []
        for i in range(10):
            diets.append(LegacyDiet.objects.create(name=f"d{i}", code=f"D{i}"))

        index = 0

        def side_effect():
            nonlocal index
            Diet.objects.create(name=f"TEST{index}", code=f"TEST{index}")
            index += 1

        mocked_import.side_effect = side_effect

        silently_call_command("importlegacy")
        self.assertEqual(mocked_import.call_count, len(diets))
        for i in range(10):
            self.assertTrue(Diet.objects.get(name=f"TEST{i}"))
