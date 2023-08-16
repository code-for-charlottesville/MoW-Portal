import datetime
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from freezegun import freeze_time

from interfaces.recurrence import (
    abbreviated_days_of_week,
    abbreviated_weeks_of_month,
    days_of_month_field_names,
    days_of_month_tuples,
)
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
from staff.forms import CreateAssignmentForm, EditMultipleAssignmentsForm, get_job_choices
from staff.views.assignment_management import (
    MultipleDayAssignment,
    Row,
    SingleDayAssignment,
    generate_assignments_display,
)
from staff.views.email import send_email


class TestManageAssignments(TestCase):
    def setUp(self):
        self.client = Client()
        self.staffuser = User.objects.get_or_create(
            username="admin",
            password="pass@123",
            email="admin@admin.com",
            is_staff=True,
        )[0]
        self.client.force_login(self.staffuser)

    def test_get_page(self):
        """
        simple get request
        __author__ = "Kyle-L45"
        """
        response = self.client.get("/staff/manage-assignments/")
        self.assertEqual(response.status_code, 200)


class TestManageAssignmentsTable(TestCase):
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
        user_1 = User.objects.get_or_create(
            username="volunteer",
            first_name="firstname1",
            last_name="lastname",
            password="mealsonwheels",
        )[0]
        self.vol_1 = Volunteer.objects.get(user=user_1)

        # create the assignment
        job_type = JobType.objects.create(name="test_type")
        self.job_1 = Job.objects.create(
            name="packer", num_vols_required=1, job_type=job_type)
        job_2 = Job.objects.create(
            name="driver",
            num_vols_required=1,
            job_type=job_type)
        self.job_1_pk = self.job_1.pk
        self.job_2_pk = job_2.pk
        day = datetime.date.today()
        self.next_day = day + datetime.timedelta(days=1)
        self.week_of_month = (day.day - 1) // 7 + 1
        self.week_of_month_next = (self.next_day.day - 1) // 7 + 1
        self.assignment_1 = Assignment.objects.create(
            job=self.job_1,
            day_of_week=day.isoweekday(),
            week_of_month=self.week_of_month)
        self.assignment_2 = Assignment.objects.create(
            job=job_2,
            day_of_week=self.next_day.isoweekday(),
            week_of_month=self.week_of_month_next,
            volunteer=self.vol_1,
        )

    def test_dipslays_assignments_no_arg(self):
        """
         table contains the assignment
        """
        res = self.client.get("/staff/manage-assignments-table/")
        self.assertContains(res, OPEN_ROUTE)
        self.assertContains(
            res,
            f"{abbreviated_weeks_of_month[self.assignment_1.week_of_month]} {abbreviated_days_of_week[self.assignment_1.day_of_week]}",
        )
        self.assertContains(
            res, f"{self.vol_1.user.first_name} {self.vol_1.user.last_name}",
        )

    def test_appends_multiple_assignments(self):
        """
         table contains the assignment
        """
        assignment_3 = Assignment.objects.create(
            job=self.job_1,
            day_of_week=self.next_day.isoweekday(),
            week_of_month=self.week_of_month_next,
        )
        res = self.client.get("/staff/manage-assignments-table/")
        self.assertContains(res, OPEN_ROUTE)
        self.assertContains(
            res,
            f"{abbreviated_weeks_of_month[self.assignment_1.week_of_month]} {abbreviated_days_of_week[self.assignment_1.day_of_week]}",
        )
        self.assertContains(
            res,
            f"{abbreviated_weeks_of_month[assignment_3.week_of_month]} {abbreviated_days_of_week[assignment_3.day_of_week]}",
        )
        self.assertContains(
            res, f"{self.vol_1.user.first_name} {self.vol_1.user.last_name}",
        )

    def test_dipslays_assignments_job_pk(self):
        """
         table contains the assignment
        """
        res = self.client.get(
            f"/staff/manage-assignments-table/{self.job_1_pk}/")
        self.assertContains(res, OPEN_ROUTE)
        self.assertContains(
            res,
            f"{abbreviated_weeks_of_month[self.assignment_1.week_of_month]} {abbreviated_days_of_week[self.assignment_1.day_of_week]}",
        )
        self.assertNotContains(
            res, f"{self.vol_1.user.first_name} {self.vol_1.user.last_name}",
        )

    def test_dipslays_assignments_vol_pk(self):
        """
         table contains the assignment
        """
        res = self.client.get(
            f"/staff/manage-assignments-table/0/{self.vol_1.pk}/")
        self.assertNotContains(res, OPEN_ROUTE)
        self.assertContains(
            res,
            f"{abbreviated_weeks_of_month[self.assignment_2.week_of_month]} {abbreviated_days_of_week[self.assignment_2.day_of_week]}",
        )
        self.assertContains(
            res, f"{self.vol_1.user.first_name} {self.vol_1.user.last_name}",
        )

    def test_dipslays_empty_table_no_arg(self):
        """
        table is empty
        """
        self.assignment_1.delete()
        self.assignment_2.delete()
        res = self.client.get("/staff/manage-assignments-table/")
        self.assertContains(res, "Nothing to display.")

    def test_dipslays_empty_table_job_pk(self):
        """
        table is empty
        """
        self.assignment_1.delete()
        res = self.client.get(
            f"/staff/manage-assignments-table/{self.job_1_pk}/")
        self.assertContains(res, "Nothing to display.")

    def test_dipslays_empty_table_vol_pk(self):
        """
        table is empty
        """
        self.assignment_2.delete()
        res = self.client.get(
            f"/staff/manage-assignments-table/0/{self.vol_1.pk}/")
        self.assertContains(res, "Nothing to display.")


class TestDisplayItems(TestCase):
    def test_str_single_day_display(self):
        """
        test string for single day assignment
        """
        sda = SingleDayAssignment(1, 2)
        self.assertEqual("1st Tue", str(sda))

    def test_str_multiple_day_display(self):
        """
        test string for single day assignment
        """
        mda = MultipleDayAssignment(1)
        self.assertEqual("Mondays", str(mda))


class TestRowSort(TestCase):
    def setUp(self):
        # create the different jobs
        routes = JobType.objects.create(name="routes")
        packers = JobType.objects.create(name="packers")
        shuttles = JobType.objects.create(name="shuttles")
        route_1 = Route.objects.create(
            number=1, name="route_1", job_type=routes)
        route_2 = Route.objects.create(
            number=2, name="route_2", job_type=routes)
        packer_1 = Job.objects.create(job_type=packers, name="apacker")
        packer_2 = Job.objects.create(job_type=packers, name="bpacker")
        shuttle = Job.objects.create(job_type=shuttles, name="shuttle")
        # create 2 vols
        user_1 = User.objects.get_or_create(
            username="volunteer1",
            first_name="aaaaaa",
            last_name="aaaaaa",
            password="mealsonwheels",
        )[0]
        vol_1 = Volunteer.objects.get(user=user_1)
        user_2 = User.objects.get_or_create(
            username="volunteer2",
            first_name="bbbbb",
            last_name="bbbbb",
            password="mealsonwheels",
        )[0]
        vol_2 = Volunteer.objects.get(user=user_2)
        # create an assignment for each one
        route_1_a_1 = Assignment.objects.create(
            day_of_week=1, week_of_month=1, job=route_1, volunteer=vol_1
        )
        route_1_a_2 = Assignment.objects.create(
            day_of_week=1, week_of_month=1, job=route_1, volunteer=vol_2
        )
        route_1_a_3 = Assignment.objects.create(
            day_of_week=1, week_of_month=1, job=route_1)
        route_2_a = Assignment.objects.create(
            day_of_week=1, week_of_month=1, job=route_2)
        packer_1_a = Assignment.objects.create(
            day_of_week=1, week_of_month=1, job=packer_1)
        packer_2_a = Assignment.objects.create(
            day_of_week=1, week_of_month=1, job=packer_2)
        shuttle_a = Assignment.objects.create(
            day_of_week=1, week_of_month=1, job=shuttle)
        # create rows
        self.row_1 = Row(route_1_a_1)
        self.row_2 = Row(route_1_a_2)
        self.row_3 = Row(route_1_a_3)
        self.row_4 = Row(route_2_a)
        self.row_5 = Row(packer_1_a)
        self.row_6 = Row(packer_2_a)
        self.row_7 = Row(shuttle_a)

    def test_route_number_order(self):
        """
        rows should display in order of route number if they are routes
        """
        self.assertTrue(self.row_1.__lt__(self.row_4))

    def test_same_job_vol_order_no_open_job(self):
        """
        rows should display in volunteer order if they are the same job
        """
        self.assertTrue(self.row_1.__lt__(self.row_2))

    def test_same_job_vol_order_open_job_caller(self):
        """
        open job should be compared alphabetically, open job calls __lt__
        """
        self.assertFalse(self.row_3.__lt__(self.row_1))

    def test_same_job_vol_order_open_job_compare(self):
        """
        open job should be compared alphabetically, filled job calls __lt__
        """
        self.assertTrue(self.row_1.__lt__(self.row_3))

    def test_routes_get_priority_route_caller(self):
        """
        routes get priority in sorting, route calls __lt__
        """
        self.assertTrue(self.row_1.__lt__(self.row_6))

    def test_routes_get_priority_route_compare(self):
        """
        routes get priority in sorting, other job calls __lt__
        """
        self.assertFalse(self.row_6.__lt__(self.row_1))

    def test_display_in_job_type_order(self):
        """
        if they aren't routes, display in job_type order
        """
        self.assertTrue(self.row_5.__lt__(self.row_7))

    def test_display_job_name_order(self):
        """
        same job type, different job name
        """
        self.assertTrue(self.row_5.__lt__(self.row_6))


class TestGenerateAssignmentDisplay(TestCase):
    def setUp(self):
        # create assignments for first 4 weeks
        job_type = JobType.objects.create(name="type")
        job = Job.objects.create(name="job", job_type=job_type)
        self.assignment_list = []
        for i in range(1, 5):
            self.assignment_list.append(SingleDayAssignment(i, 1))

    def test_not_all_5_weeks(self):
        """
        shouldn't condense anything
        """
        self.assertEqual(
            "1st Mon, 2nd Mon, 3rd Mon, 4th Mon",
            generate_assignments_display(self.assignment_list),
        )

    def test_condenses_day_of_week(self):
        """
        should take all days and condense to mondays
        """
        self.assertEqual("Mondays", generate_assignments_display(
            self.assignment_list + [SingleDayAssignment(5, 1)]), )


class TestCreateRecurrence(TestCase):
    def setUp(self):
        self.client = Client()
        self.staffuser = User.objects.get_or_create(
            username="admin",
            password="pass@123",
            email="admin@admin.com",
            is_staff=True,
        )[0]
        self.client.force_login(self.staffuser)

    def test_get_request(self):
        """
        simple get request to the page
        """
        res = self.client.get("/staff/recurrences/create/")
        self.assertContains(res, "Create Assignment")
        self.assertEqual(200, res.status_code)

    @patch("staff.forms.CreateAssignmentForm.is_valid")
    def test_post_request_valid(self, mock):
        """
        simple post request to the page
        should redirect to manage assignments if valid
        """
        mock.return_value = True
        res = self.client.post("/staff/recurrences/create/", follow=True)
        self.assertRedirects(res, "/staff/manage-assignments/")

    @patch("staff.forms.CreateAssignmentForm.is_valid")
    def test_post_request_invalid(self, mock):
        """
        simple post request to the page
        should stay on create assignment when invalid
        """
        mock.return_value = False
        res = self.client.post("/staff/recurrences/create/", follow=True)
        self.assertContains(res, "Create Assignment")


class TestEditMultipleAssignments(TestCase):
    def setUp(self):
        self.client = Client()
        self.staffuser = User.objects.get_or_create(
            username="admin",
            password="pass@123",
            email="admin@admin.com",
            is_staff=True,
        )[0]
        self.client.force_login(self.staffuser)
        job_type = JobType.objects.create(name="job")
        self.job = Job.objects.create(job_type=job_type, name="job")
        # create a volunteer
        user = User.objects.get_or_create(
            username="volunteer",
            first_name="firstname1",
            last_name="lastname",
            password="mealsonwheels",
        )[0]
        self.vol = Volunteer.objects.get(user=user)
        Assignment.objects.create(
            job=self.job, volunteer=self.vol, day_of_week=1, week_of_month=1
        )
        Assignment.objects.create(
            job=self.job, volunteer=self.vol, day_of_week=1, week_of_month=2
        )
        Assignment.objects.create(
            job=self.job,
            volunteer=None,
            day_of_week=2,
            week_of_month=1)
        Assignment.objects.create(
            job=self.job,
            volunteer=None,
            day_of_week=2,
            week_of_month=2)

    def test_job_not_found(self):
        """
        should return 404
        """
        res = self.client.get(
            f"/staff/edit-multiple-assignments/{self.job.pk + 1}/")
        self.assertEqual(res.status_code, 404)

    def test_not_assignments_found(self):
        """
        should return 404
        """
        user = User.objects.get_or_create(
            username="volunteer1111",
            first_name="firstname1",
            last_name="lastname",
            password="mealsonwheels",
        )[0]
        vol = Volunteer.objects.get(user=user)
        res = self.client.get(
            f"/staff/edit-multiple-assignments/{self.job.pk}/{vol.pk}/")
        self.assertEqual(res.status_code, 404)

    def test_vol_not_found(self):
        """
        should return 404
        """
        res = self.client.get(
            f"/staff/edit-multiple-assignments/{self.job.pk}/{self.vol.pk + 1}/"
        )
        self.assertEqual(res.status_code, 404)

    def test_get_request_volunteer_valid(self):
        """
        simple get request to the page for vol
        """
        res = self.client.get(
            f"/staff/edit-multiple-assignments/{self.job.pk}/{self.vol.pk}/")
        # this volunteer was assigned the first monday and second monday
        self.assertContains(res, "First Monday")
        self.assertNotContains(res, "First Tuesday")
        self.assertContains(res, "Second Monday")
        self.assertNotContains(res, "Second Tuesday")

    def test_get_request_volunteer_open_job(self):
        """
        simple get request to the page for open job
        """
        res = self.client.get(
            f"/staff/edit-multiple-assignments/{self.job.pk}/")
        # open job was assigned the first tuesday and second tuesday
        self.assertNotContains(res, "First Monday")
        self.assertContains(res, "First Tuesday")
        self.assertNotContains(res, "Second Monday")
        self.assertContains(res, "Second Tuesday")

    @patch("staff.forms.EditMultipleAssignmentsForm.is_valid")
    def test_post_request_edit_valid(self, mock):
        """
        valid form redirect
        """
        mock.return_value = True
        res = self.client.post(
            f"/staff/edit-multiple-assignments/{self.job.pk}/",
            follow=True)
        # should redirect to manage assignments
        self.assertRedirects(res, "/staff/manage-assignments/")

    @patch("staff.forms.EditMultipleAssignmentsForm.is_valid")
    def test_post_request_edit_invalid(self, mock):
        """
        invalid form
        """
        mock.return_value = False
        res = self.client.post(
            f"/staff/edit-multiple-assignments/{self.job.pk}/",
            follow=True)
        # open job was assigned the first tuesday and second tuesday
        self.assertNotContains(res, "First Monday")
        self.assertContains(res, "First Tuesday")
        self.assertNotContains(res, "Second Monday")
        self.assertContains(res, "Second Tuesday")

    def test_post_request_delete_valid(self):
        """
        delete is passed a valid arg
        """
        args = {"delete_assignments": True, "second_tuesday": True}
        res = self.client.post(
            f"/staff/edit-multiple-assignments/{self.job.pk}/",
            args,
            follow=True)
        # should redirect to manage assignments
        self.assertRedirects(res, "/staff/manage-assignments/")
        # second tuesday assignment should be deleted for open job
        with self.assertRaises(Assignment.DoesNotExist):
            Assignment.objects.get(
                volunteer=None, job=self.job, day_of_week=2, week_of_month=2
            )

    def test_post_request_delete_invalid(self):
        """
        delete is passed invalid assignment arg
        """
        args = {"delete_assignments": True, "third_monday": True}
        res = self.client.post(
            f"/staff/edit-multiple-assignments/{self.job.pk}/",
            args,
            follow=True)
        # should redirect to manage assignments
        self.assertRedirects(res, "/staff/manage-assignments/")
        # nothing should be deleted
        Assignment.objects.get(
            job=self.job,
            volunteer=None,
            day_of_week=2,
            week_of_month=1)
        Assignment.objects.get(
            job=self.job,
            volunteer=None,
            day_of_week=2,
            week_of_month=2)

    def test_post_request_delete_invalid_and_valid(self):
        """
        delete is passed invalid and valid assignment arg
        """
        args = {
            "delete_assignments": True,
            "third_monday": True,
            "second_tuesday": True}
        res = self.client.post(
            f"/staff/edit-multiple-assignments/{self.job.pk}/",
            args,
            follow=True)
        # should redirect to manage assignments
        self.assertRedirects(res, "/staff/manage-assignments/")
        # second tuesday should be deleted
        with self.assertRaises(Assignment.DoesNotExist):
            Assignment.objects.get(
                job=self.job, volunteer=None, day_of_week=2, week_of_month=2
            )
        # first tuesday should not be deleted
        Assignment.objects.get(
            job=self.job,
            volunteer=None,
            day_of_week=2,
            week_of_month=1)


class TestJobChoices(TestCase):
    def setUp(self):
        # placeholder in form
        self.res = [(None, "Please select a job.")]

    def test_get_normal_job(self):
        """
        test that it handles the other job case properly
        """
        other_job_type = JobType.objects.create(name="other")
        job = Job.objects.create(job_type=other_job_type, name="job")
        self.assertEqual(self.res + [(job.pk, "job")], get_job_choices())

    def test_get_route_job(self):
        """
        test that it handles the route case properly
        """
        route_type = JobType.objects.create(name="Route")
        job = Route.objects.create(job_type=route_type, name="job", number=1)
        self.assertEqual(self.res + [(job.pk, "job")], get_job_choices())

    def test_routes_first(self):
        """
        routes should be displayed first
        """
        other_job_type = JobType.objects.create(name="other")
        job = Job.objects.create(job_type=other_job_type, name="job")
        route_type = JobType.objects.create(name="Route")
        route = Route.objects.create(
            job_type=route_type, name="route", number=1)
        self.assertEqual(
            self.res + [(route.pk, "route"), (job.pk, "job")], get_job_choices())


class TestCreateAssignmentForm(TestCase):
    def setUp(self):
        job_type = JobType.objects.create(name="type")
        self.job = Job.objects.create(job_type=job_type, name="job")

    def test_creates_open_job_assignment(self):
        form = CreateAssignmentForm({"job": self.job.pk, "first_monday": True})
        self.assertTrue(form.is_valid())
        Assignment.objects.get(
            volunteer=None,
            week_of_month=1,
            day_of_week=1,
            job=self.job)

    def test_creates_vol_assignment(self):
        user = User.objects.get_or_create(
            username="volunteer",
            first_name="firstname1",
            last_name="lastname",
            password="mealsonwheels",
        )[0]
        vol = Volunteer.objects.get(user=user)
        form = CreateAssignmentForm(
            {"job": self.job.pk, "first_monday": True, "volunteer": vol.pk}
        )
        self.assertTrue(form.is_valid())
        Assignment.objects.get(
            volunteer=vol,
            week_of_month=1,
            day_of_week=1,
            job=self.job)

    def test_creates_only_valid_assignments(self):
        """
        should not do anything with invalid data, but still create valid assignments
        """
        form = CreateAssignmentForm(
            {"job": self.job.pk, "first_monday": True, "sixth_monday": True}
        )
        self.assertTrue(form.is_valid())
        Assignment.objects.get(
            volunteer=None,
            week_of_month=1,
            day_of_week=1,
            job=self.job)
        self.assertEqual(1, Assignment.objects.all().count())

    def test_invalid_job_pk_number(self):
        form = CreateAssignmentForm({"job": 0, "first_monday": True})
        self.assertFalse(form.is_valid())

    def test_invalid_job_not_passed(self):
        form = CreateAssignmentForm({"first_monday": True})
        self.assertFalse(form.is_valid())

    def test_invalid_job_type(self):
        form = CreateAssignmentForm({"job": "job", "first_monday": True})
        self.assertFalse(form.is_valid())

    def test_invalid_volunteer_type(self):
        form = CreateAssignmentForm(
            {"job": self.job.pk, "first_monday": True, "volunteer": "volunteer"}
        )
        self.assertFalse(form.is_valid())

    def test_can_create_all_fields(self):
        args = {"job": self.job.pk}
        for key in days_of_month_field_names:
            if "sunday" in days_of_month_field_names[key] or "saturday" in days_of_month_field_names[key]:
                continue
            args[days_of_month_field_names[key]] = True
        form = CreateAssignmentForm(args)
        self.assertTrue(form.is_valid())
        for key in days_of_month_tuples:
            if days_of_month_tuples[key].day_of_week == 6 or days_of_month_tuples[key].day_of_week == 7:
                continue
            Assignment.objects.get(
                week_of_month=days_of_month_tuples[key].week_of_month,
                day_of_week=days_of_month_tuples[key].day_of_week,
                job=self.job.pk,
            )


class TestEditMultipleAssignmentsForm(TestCase):
    def setUp(self):
        job_type = JobType.objects.create(name="type")
        self.job = Job.objects.create(job_type=job_type, name="job")
        # create a volunteer
        user = User.objects.get_or_create(
            username="volunteer",
            first_name="firstname1",
            last_name="lastname",
            password="mealsonwheels",
        )[0]
        self.vol = Volunteer.objects.get(user=user)
        a = Assignment.objects.create(
            job=self.job, day_of_week=1, week_of_month=1, volunteer=self.vol
        )
        self.assignments_list = Assignment.objects.all()

    def test_valid_set_to_open_job(self):
        """
        should set the assignment to open job
        """
        form = EditMultipleAssignmentsForm(
            self.assignments_list, {
                "first_monday": True})
        self.assertTrue(form.is_valid())
        self.assertIsNone(
            Assignment.objects.get(
                job=self.job,
                day_of_week=1,
                week_of_month=1).volunteer)

    def test_valid_set_to_new_vol(self):
        """
        should set the assignment vol to the new vol
        """
        user = User.objects.get_or_create(
            username="volunteer11111",
            first_name="firstname1",
            last_name="lastname",
            password="mealsonwheels",
        )[0]
        vol = Volunteer.objects.get(user=user)
        form = EditMultipleAssignmentsForm(
            self.assignments_list, {"first_monday": True, "volunteer": vol.pk}
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(
            Assignment.objects.get(
                job=self.job,
                day_of_week=1,
                week_of_month=1).volunteer,
            vol)

    def test_invalid_volunteer_pk(self):
        """
        should set the assignment to open job
        """
        form = EditMultipleAssignmentsForm(
            self.assignments_list, {"first_monday": True, "volunteer": 0}
        )
        self.assertFalse(form.is_valid())

    def test_invalid_volunteer_type(self):
        """
        should set the assignment to open job
        """
        form = EditMultipleAssignmentsForm(
            self.assignments_list, {
                "first_monday": True, "volunteer": "volunteer"})
        self.assertFalse(form.is_valid())

    def test_assignment_does_not_exist(self):
        """
        nothing should happen, the form will ignore
        """
        form = EditMultipleAssignmentsForm(
            self.assignments_list, {
                "second_monday": True})
        form.is_valid()
        Assignment.objects.get(
            job=self.job, day_of_week=1, week_of_month=1, volunteer=self.vol
        )
