import datetime
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


class TestManageSubstitutions(TestCase):
    def setUp(self):
        self.client = Client()
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
        vol = Volunteer.objects.get(user=user)
        job_type = JobType.objects.create(name="test_type")
        route_type = JobType.objects.create(name="Route")
        job = Job.objects.create(
            name="packer",
            num_vols_required=1,
            job_type=job_type)
        route = Route.objects.create(
            name="route 1", number=1, job_type=route_type)
        day = datetime.date.today()
        week_of_month = (day.day - 1) // 7 + 1
        assignment_1 = Assignment.objects.create(
            job=job, day_of_week=day.isoweekday(), week_of_month=week_of_month
        )
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        week_of_month = (tomorrow.day - 1) // 7 + 1
        assignment_2 = Assignment.objects.create(
            job=route,
            day_of_week=tomorrow.isoweekday(),
            week_of_month=week_of_month)
        self.sub = Substitution.objects.create(
            date=day, assignment=assignment_1, volunteer=vol)
        self.sub_2 = Substitution.objects.create(
            date=tomorrow, assignment=assignment_2)

    def test_get_manage_subs_page(self):
        """
        simple get request to the page when the substitution is filled
        """
        response = self.client.get("/staff/manage-substitutions/")
        self.assertContains(response, "firstname lastname")
        # testing that the substitution is displayed accurately
        self.assertEqual(response.status_code, 200)

    def test_get_manage_subs_page_open_sub(self):
        """
        simple get request to the page when the substitution is open
        """
        self.sub.volunteer = None
        self.sub.save()
        response = self.client.get("/staff/manage-substitutions/")
        # testing that the substitution is displayed accurately
        self.assertContains(response, "OPEN")
        self.assertContains(response, '<tr class="danger">')
        # row is red when not filled
        self.assertEqual(response.status_code, 200)


class TestDeleteSubstitution(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.force_login(
            User.objects.get_or_create(
                username="admin",
                password="pass@123",
                email="admin@admin.com",
                is_staff=True,
            )[0])
        # login as staff
        # create a substitution object
        job_type = JobType.objects.create(name="test_type")
        job = Job.objects.create(
            name="packer",
            num_vols_required=1,
            job_type=job_type)
        day = datetime.date.today()
        week_of_month = (day.day - 1) // 7 + 1
        assignment = Assignment.objects.create(
            job=job, day_of_week=day.isoweekday(), week_of_month=week_of_month
        )
        self.sub = Substitution.objects.create(date=day, assignment=assignment)

    def test_delete_success(self):
        """
        successful deletion of substitution
        """
        sub_pk = self.sub.pk
        res = self.client.get(f"/staff/delete-substitution/{sub_pk}/")
        self.assertRedirects(res, "/staff/manage-substitutions/")
        with self.assertRaises(Substitution.DoesNotExist):
            Substitution.objects.get(pk=sub_pk)

    def test_delete_404(self):
        """
        pk not found, should 404
        """
        res = self.client.get(f"/staff/delete-substitution/{self.sub.pk + 1}/")
        self.assertEqual(res.status_code, 404)


class TestRemoveSubstitute(TestCase):
    def setUp(self):
        self.client = Client()
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
        # create a substitution object
        job_type = JobType.objects.create(name="test_type")
        job = Job.objects.create(
            name="packer",
            num_vols_required=1,
            job_type=job_type)
        day = datetime.date.today()
        week_of_month = (day.day - 1) // 7 + 1
        assignment = Assignment.objects.create(
            job=job, day_of_week=day.isoweekday(), week_of_month=week_of_month
        )
        self.sub = Substitution.objects.create(
            date=day, assignment=assignment, volunteer=self.vol
        )

    def test_remove_sub_success(self):
        """
        remove vol from sub that is filled
        """
        res = self.client.get(f"/staff/remove-substitute/{self.sub.pk}/")
        self.assertRedirects(res, "/staff/manage-substitutions/")
        self.sub.refresh_from_db()
        self.assertIsNone(self.sub.volunteer)

    def test_remove_sub_success_open_already(self):
        """
        should not error, just redirect like normal
        """
        self.sub.volunteer = None
        self.sub.save()
        res = self.client.get(f"/staff/remove-substitute/{self.sub.pk}/")
        self.assertRedirects(res, "/staff/manage-substitutions/")
        self.sub.refresh_from_db()
        self.assertIsNone(self.sub.volunteer)

    def test_remove_sub_not_found(self):
        """
        sub doesn't exist
        """
        res = self.client.get(f"/staff/remove-substitute/{self.sub.pk + 1}/")
        self.assertEqual(res.status_code, 404)


class TestSpawnOpenJobs(TestCase):
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
        # create a volunteer
        self.vol = Volunteer.objects.get(user=user)
        # create a substitution object
        job_type = JobType.objects.create(name="test_type")
        job = Job.objects.create(
            name="packer",
            num_vols_required=1,
            job_type=job_type)
        self.day_1 = datetime.date.today()
        week_of_month = (self.day_1.day - 1) // 7 + 1
        self.assignment_1 = Assignment.objects.create(
            job=job, day_of_week=self.day_1.isoweekday(), week_of_month=week_of_month)
        self.day_2 = self.day_1 + datetime.timedelta(days=1)
        week_of_month = (self.day_2.day - 1) // 7 + 1
        self.assignment_2 = Assignment.objects.create(
            job=job, day_of_week=self.day_2.isoweekday(), week_of_month=week_of_month)

    def test_get_request(self):
        """
        simple get request to the page
        """
        self.assertEqual(200, self.client.get(
            "/staff/spawn-open-jobs/").status_code)

    def test_form_invalid(self):
        """
        when form is invalid, should not redirect
        """
        self.assertEqual(
            200,
            self.client.post(
                "/staff/spawn-open-jobs/",
                follow=True).status_code)

    def test_form_valid_one_day(self):
        """
        should create sub
        """
        res = self.client.post(
            "/staff/spawn-open-jobs/",
            {"begin_date": self.day_1, "end_date": self.day_1},
            follow=True,
        )
        self.assertRedirects(res, "/staff/manage-substitutions/")
        # only creates 1
        Substitution.objects.get(
            date=self.day_1,
            volunteer=None,
            assignment=self.assignment_1)
        # should not create
        self.assertEqual(
            0, Substitution.objects.filter(
                assignment=self.assignment_2).count())

    def test_form_valid_one_day_no_duplicate(self):
        """
        should not duplicate sub
        """
        Substitution.objects.create(
            assignment=self.assignment_1,
            date=self.day_1)
        res = self.client.post(
            "/staff/spawn-open-jobs/",
            {"begin_date": self.day_1, "end_date": self.day_1},
            follow=True,
        )
        self.assertRedirects(res, "/staff/manage-substitutions/")
        # only creates 1
        Substitution.objects.get(
            date=self.day_1,
            volunteer=None,
            assignment=self.assignment_1)
        # should not create
        self.assertEqual(
            0, Substitution.objects.filter(
                assignment=self.assignment_2).count())

    def test_form_valid_loop(self):
        """
        should create both
        """
        Substitution.objects.create(
            assignment=self.assignment_1,
            date=self.day_1)
        res = self.client.post(
            "/staff/spawn-open-jobs/",
            {"begin_date": self.day_1, "end_date": self.day_2},
            follow=True,
        )
        self.assertRedirects(res, "/staff/manage-substitutions/")
        # only creates 1
        Substitution.objects.get(
            date=self.day_1,
            volunteer=None,
            assignment=self.assignment_1)
        # only creates 1
        Substitution.objects.get(
            date=self.day_2,
            volunteer=None,
            assignment=self.assignment_2)

    def test_no_historical(self):
        """
        should not allow historical dates
        """
        res = self.client.post(
            "/staff/spawn-open-jobs/",
            {"begin_date": self.day_1 - datetime.timedelta(days=1), "end_date": self.day_1},
            follow=True,
        )
        self.assertEqual(200, res.status_code)
        with self.assertRaises(Substitution.DoesNotExist):
            Substitution.objects.get(
                date=self.day_1, volunteer=None, assignment=self.assignment_1
            )
            # only creates 1
            Substitution.objects.get(
                date=self.day_2, volunteer=None, assignment=self.assignment_2
            )

    def test_begin_date_after_end_date(self):
        """
        should not allow historical dates
        """
        res = self.client.post(
            "/staff/spawn-open-jobs/",
            {"begin_date": self.day_2, "end_date": self.day_1},
            follow=True,
        )
        self.assertEqual(200, res.status_code)
        with self.assertRaises(Substitution.DoesNotExist):
            Substitution.objects.get(
                date=self.day_1, volunteer=None, assignment=self.assignment_1
            )
            # only creates 1
            Substitution.objects.get(
                date=self.day_2, volunteer=None, assignment=self.assignment_2
            )


class TestAsyncParseAssignment(TestCase):
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
        # create a volunteer
        self.vol = Volunteer.objects.get(user=user)
        # create a substitution object
        job_type = JobType.objects.create(name="test_type")
        self.job = Job.objects.create(
            name="packer",
            num_vols_required=1,
            job_type=job_type)
        self.day_1 = datetime.date.today()
        week_of_month = (self.day_1.day - 1) // 7 + 1
        self.assignment_1 = Assignment.objects.create(
            job=self.job,
            day_of_week=self.day_1.isoweekday(),
            week_of_month=week_of_month,
            volunteer=self.vol,
        )
        self.assignment_2 = Assignment.objects.create(
            job=self.job,
            day_of_week=self.day_1.isoweekday(),
            week_of_month=week_of_month)
        self.sub = Substitution.objects.create(
            assignment=self.assignment_1, date=self.day_1)
        self.date_str = self.day_1.strftime("%Y-%m-%d")

    def test_invalid_date(self):
        """
        should return an error
        """
        res = self.client.get(
            f"/staff/async-parse-assignment/not-a-date/{self.job.pk}/"
        ).content
        res = json.loads(res)
        self.assertEqual(res["status"], "error")

    def test_invalid_job(self):
        """
        should return an error
        """
        res = self.client.get(
            "/staff/async-parse-assignment/2020-01-01/0/").content
        res = json.loads(res)
        self.assertEqual(res["status"], "error")

    def test_gets_assignment_vols_and_subs(self):
        """
        should get list of volunteers and open jobs for the date and job
        and return a count of substitutions
        """
        res = self.client.get(
            f"/staff/async-parse-assignment/{self.date_str}/{self.job.pk}/"
        ).content
        res = json.loads(res)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["sub_count"], 1)
        for a in res["vols"]:
            self.assertTrue(
                a
                in [
                    {
                        "vol_name": str(self.assignment_1.volunteer),
                        "vol_pk": self.assignment_1.volunteer.pk,
                    },
                    {"vol_name": OPEN_ROUTE, "vol_pk": ""},
                ]
            )


class TestCreateSubtitution(TestCase):
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
        # create a volunteer
        self.vol = Volunteer.objects.get(user=user)
        # create a substitution object
        job_type = JobType.objects.create(name="test_type")
        self.job = Job.objects.create(
            name="packer",
            num_vols_required=1,
            job_type=job_type)
        self.day_1 = datetime.date.today()
        week_of_month = (self.day_1.day - 1) // 7 + 1
        self.assignment_1 = Assignment.objects.create(
            job=self.job,
            day_of_week=self.day_1.isoweekday(),
            week_of_month=week_of_month)

    def test_get_request(self):
        """
        get request to the page
        """
        res = self.client.get("/staff/create-substitution/")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Create Substitution")

    def test_missing_data(self):
        """
        invalid form, missing data
        """
        res = self.client.post("/staff/create-substitution/", {}, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Create Substitution")

    def test_valid_form(self):
        """
        valid form
        """
        res = self.client.post(
            "/staff/create-substitution/",
            {"job": self.job.pk, "date": self.day_1, "substitute": self.vol.pk},
            follow=True,
        )
        self.assertRedirects(res, "/staff/manage-substitutions/")
        Substitution.objects.get(
            date=self.day_1, assignment=self.assignment_1, volunteer=self.vol
        )

    def test_no_date_given(self):
        """
        Should go back to create sub
        """
        res = self.client.post(
            "/staff/create-substitution/",
            {"job": self.job.pk, "substitute": self.vol.pk, "assigned_volunteer": ""},
            follow=True,
        )
        # should give attribute error
        self.assertContains(res, "Create Substitution")

    def test_cannot_find_assignment(self):
        """
        invalid form, should go back to Create Sub
        """
        res = self.client.post(
            "/staff/create-substitution/",
            {
                "job": self.job.pk,
                "date": self.day_1,
                "substitute": self.vol.pk,
                "assigned_volunteer": self.vol.pk,
            },
            follow=True,
        )
        self.assertContains(res, "Create Substitution")


class TestEditSubstitution(TestCase):
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
        # create a volunteer
        self.vol = Volunteer.objects.get(user=user)
        user2 = User.objects.get_or_create(
            username="volunteer1",
            first_name="firstname",
            last_name="lastname",
            password="mealsonwheels",
        )[0]
        # create a volunteer
        self.vol2 = Volunteer.objects.get(user=user2)
        # create a substitution object
        job_type = JobType.objects.create(name="test_type")
        self.job = Job.objects.create(
            name="packer",
            num_vols_required=1,
            job_type=job_type)
        self.day_1 = datetime.date.today()
        week_of_month = (self.day_1.day - 1) // 7 + 1
        self.assignment_1 = Assignment.objects.create(
            job=self.job,
            day_of_week=self.day_1.isoweekday(),
            week_of_month=week_of_month,
            volunteer=self.vol,
        )
        self.sub = Substitution.objects.create(
            date=self.day_1, assignment=self.assignment_1, volunteer=self.vol2
        )

    def test_sub_not_found(self):
        """
        should 404
        """
        self.assertEqual(404, self.client.get(
            "/staff/edit-substitution/0/").status_code)

    def test_get_request(self):
        """
        get request to the page
        """
        res = self.client.get(f"/staff/edit-substitution/{self.sub.pk}/")
        self.assertEqual(200, res.status_code)
        self.assertContains(res, "Edit Substitution")

    def test_invalid_form(self):
        """
        post request to the page, form invalid
        """
        res = self.client.post(
            f"/staff/edit-substitution/{self.sub.pk}/", {"volunteer": 0}, follow=True
        )
        self.assertEqual(200, res.status_code)
        self.assertContains(res, "Edit Substitution")

    def test_open_up_sub(self):
        """
        post request to the page, form invalid
        """
        res = self.client.post(
            f"/staff/edit-substitution/{self.sub.pk}/",
            {},
            follow=True)
        self.assertRedirects(res, "/staff/manage-substitutions/")
        self.sub.refresh_from_db()
        self.assertIsNone(self.sub.volunteer)

    def test_change_sub(self):
        """
        post request to the page, form invalid
        """
        self.sub.volunteer = None
        self.sub.save()
        res = self.client.post(
            f"/staff/edit-substitution/{self.sub.pk}/",
            {"volunteer": self.vol2.pk},
            follow=True,
        )
        self.assertRedirects(res, "/staff/manage-substitutions/")
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.volunteer, self.vol2)
