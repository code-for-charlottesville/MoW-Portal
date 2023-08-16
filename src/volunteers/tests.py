import datetime

from django.test import Client, TestCase
from django.urls import reverse
from freezegun import freeze_time

from interfaces.recurrence import date_to_day_of_month, day_of_month_to_date
from models.models import Assignment, Job, JobType, Route, Substitution, User, Volunteer

from . import views

# Create your tests here.


class TestIndexPage(TestCase):
    def setUp(self):
        client = Client()
        self.test_volunteer = User.objects.get_or_create(
            username="test_request_user",
            password="password",
            email="admin@admin.com",
            is_staff=False,
        )[0]
        self.client.force_login(self.test_volunteer)

    def test_get_index_page_open_sub(self):
        """ simple get request to the page """
        job_type = JobType.objects.create(name="test_type")
        job = Job.objects.create(
            name="packer",
            num_vols_required=1,
            job_type=job_type)
        day = datetime.date.today()
        if day.isoweekday() == 6 or day.isoweekday() == 7:
            day = day + datetime.timedelta(days=2)  # will always be weekday
        week_of_month = (day.day - 1) // 7 + 1
        assignment = Assignment.objects.create(
            job=job, day_of_week=day.isoweekday(), week_of_month=week_of_month
        )
        sub = Substitution.objects.create(
            date=day, assignment=assignment, volunteer=None)
        response = self.client.get("/volunteer/")
        self.assertEqual(response.status_code, 200)

        # weekend days should not be included
        self.assertFalse(b"Saturday" in response.content)
        self.assertFalse(b"Sunday" in response.content)

        self.assertTrue(b"packer needs a sub." in response.content)


class TestRequest(TestCase):
    def setUp(self):
        self.client = Client()
        self.test_volunteer = User.objects.get_or_create(
            username="test_request_user",
            password="password",
            email="admin@admin.com",
            is_staff=False,
        )[0]
        self.client.force_login(self.test_volunteer)

    def test_my_jobs_path(self):
        response = self.client.get("/volunteer/my_jobs/")
        self.assertEqual(response.status_code, 200)

    def test_wrong_jobs_path(self):
        response = self.client.get("/my_jobs/")
        self.assertEqual(response.status_code, 404)

    def test_no_jobs_response(self):
        response = self.client.get("/volunteer/my_jobs/")
        self.assertContains(response, "no jobs")

    def test_no_jobs_to_show(self):
        response = self.client.get("/volunteer/my_jobs/")
        self.assertContains(response, "no jobs")

    def test_jobs_to_show(self):
        """ This test creates a job and recurring assignment for that volunteer and ensures that that job exists in the table rendered. """
        job_type = JobType.objects.create(name="test_type")
        job = Job.objects.create(
            name="test request job", num_vols_required=1, job_type=job_type
        )
        job.save()
        recurring = Assignment(
            volunteer=self.test_volunteer.volunteer,
            job_id=job.pk,
            day_of_week=date_to_day_of_month(
                datetime.date.today()).day_of_week,
            week_of_month=date_to_day_of_month(
                datetime.date.today()).week_of_month,
        )
        recurring.save()
        response = self.client.get("/volunteer/my_jobs/")
        self.assertContains(response, "test request job")

    def test_job_with_other_user(self):
        """ This test creates a job and recurring assignment for a different user and ensures that that job does not show up in the table. """
        some_other_user = User.objects.get_or_create(
            username="some_other_user",
            password="password",
            email="other@admin.com",
            is_staff=False,
        )[0]
        job_type = JobType.objects.create(name="test_type")
        job = Job.objects.create(
            name="test request job", num_vols_required=1, job_type=job_type
        )
        job.save()
        recurring = Assignment(
            volunteer=some_other_user.volunteer,
            job_id=job.pk,
            day_of_week=1,
            week_of_month=2,
        )
        recurring.save()
        response = self.client.get("/volunteer/my_jobs/")
        self.assertContains(response, "")

    def test_wrong_create_sub_path(self):
        response = self.client.get("volunteer/my_jobs/request_substitute/")
        self.assertEqual(response.status_code, 404)

    def test_displays_date(self):
        job_type = JobType.objects.create(name="test_type")
        job = Job.objects.create(
            name="test request job", num_vols_required=1, job_type=job_type
        )
        job.save()
        recurring = Assignment(
            volunteer=self.test_volunteer.volunteer,
            job_id=job.pk,
            # day_of_week=3, #these need to match the date object below
            # week_of_month=3,
            day_of_week=date_to_day_of_month(
                datetime.date.today()).day_of_week,
            week_of_month=date_to_day_of_month(
                datetime.date.today()).week_of_month,
        )
        recurring.save()
        response = self.client.get("/volunteer/my_jobs/")
        date = day_of_month_to_date(
            recurring.to_day_of_month(),
            datetime.datetime.now().month,
            datetime.datetime.now().year,
        )
        self.assertContains(response, date.strftime("%b. %d, %Y"))

    def test_displays_request_button(self):
        # test that a job with no sub request displays button
        job_type = JobType.objects.create(name="test_type")
        job = Job.objects.create(
            name="test request job", num_vols_required=1, job_type=job_type
        )
        job.save()
        recurring = Assignment(
            volunteer=self.test_volunteer.volunteer,
            job_id=job.pk,
            day_of_week=date_to_day_of_month(
                datetime.date.today()).day_of_week,
            week_of_month=date_to_day_of_month(
                datetime.date.today()).week_of_month,
        )
        recurring.save()
        response = self.client.get("/volunteer/my_jobs/")
        self.assertContains(response, "Request Substitute")

    def test_only_subs(self):
        job_type = JobType.objects.create(name="test_type")
        job = Job.objects.create(
            name="TEST NAME OF JOB", num_vols_required=1, job_type=job_type
        )
        day = datetime.date.today()
        if day.isoweekday() == 6 or day.isoweekday() == 7:
            day = day + datetime.timedelta(days=2)
        week_of_month = (day.day - 1) // 7 + 1
        assignment = Assignment.objects.create(
            job=job, day_of_week=day.isoweekday(), week_of_month=week_of_month
        )
        sub = Substitution(
            volunteer=self.test_volunteer.volunteer,
            assignment=assignment,
            date=datetime.date.today(),
        )
        sub.save()
        response = self.client.get("/volunteer/my_jobs/")
        self.assertContains(response, "Substitution")

    def test_displays_correct_job_name(self):
        job_type = JobType.objects.create(name="test_type")
        job = Job.objects.create(
            name="TEST NAME OF JOB", num_vols_required=1, job_type=job_type
        )
        job.save()
        recurring = Assignment(
            volunteer=self.test_volunteer.volunteer,
            job_id=job.pk,
            day_of_week=date_to_day_of_month(
                datetime.date.today()).day_of_week,
            week_of_month=date_to_day_of_month(
                datetime.date.today()).week_of_month,
        )
        recurring.save()
        response = self.client.get("/volunteer/my_jobs/")
        self.assertContains(response, "TEST NAME OF JOB")

    def test_does_not_display_past_job(self):
        """
        This test ensures that jobs that have already passed this month are not shown.
        """
        __author__ = "Nate Strawser"
        job_type = JobType.objects.create(name="test_type")
        job = Job.objects.create(
            name="job this month",
            num_vols_required=1,
            job_type=job_type)
        job.save()
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        recurring = Assignment(
            volunteer=self.test_volunteer.volunteer,
            job_id=job.pk,
            day_of_week=date_to_day_of_month(yesterday).day_of_week,
            week_of_month=date_to_day_of_month(yesterday).week_of_month,
        )
        recurring.save()
        response = self.client.get("/volunteer/my_jobs/")
        self.assertNotContains(response, "job this month")

    def test_enforce_login_in_volunteer_views(self):
        """
        Ensures volunteers are logged in when they view their jobs page.
        """
        __author__ = "Nate Strawser"
        self.client.logout()
        response = self.client.get("/volunteer/my_jobs/")
        self.assertEqual(response.status_code, 302)

    def test_view_jobs_when_logged_in(self):
        __author__ = "Nate Strawser"
        response = self.client.get("/volunteer/my_jobs/")
        self.assertEqual(response.status_code, 200)

    def test_route_link_shown(self):
        """
        This test ensures the correct route link is shown on the my_jobs page.
        """
        __author__ = "Nate Strawser"
        job_type = JobType.objects.create(name="test_type")
        job = Route.objects.create(
            name="Test Route", number=1, job_type=job_type)
        job.save()
        recurring = Assignment(
            volunteer=self.test_volunteer.volunteer,
            job_id=job.pk,
            day_of_week=date_to_day_of_month(
                datetime.date.today()).day_of_week,
            week_of_month=date_to_day_of_month(
                datetime.date.today()).week_of_month,
        )
        recurring.save()
        response = self.client.get("/volunteer/my_jobs/")
        self.assertContains(response, f"/routes/{job.number}/")

    def test_non_route_does_not_link(self):
        """
        This test ensures that links are not generated for non-route jobs.
        """
        __author__ = "Nate Strawser"
        job_type = JobType.objects.create(name="test_type")
        job = Job.objects.create(
            name="Test Job",
            num_vols_required=1,
            job_type=job_type)
        job.save()
        recurring = Assignment(
            volunteer=self.test_volunteer.volunteer,
            job_id=job.pk,
            day_of_week=date_to_day_of_month(
                datetime.date.today()).day_of_week,
            week_of_month=date_to_day_of_month(
                datetime.date.today()).week_of_month,
        )
        recurring.save()
        response = self.client.get("/volunteer/my_jobs/")
        self.assertNotContains(response, "/routes/")

    @freeze_time("2020-03-20")
    def test_view_open_jobs(self):
        """
        This test does the following:
            - creates a new job for a date in the future
            - requests a substitute for that job
            - checks to ensure that this job shows up as an open job

        (NOTE: This won't work if you use the current date for everything; it'll be filtered out)
        """
        __author__ = "Nate Strawser"
        future_date = datetime.date(2020, 3, 24)  # some "future" date
        job_type = JobType.objects.create(name="test_type")
        job = Job.objects.create(
            name="Test Open Job 1", num_vols_required=1, job_type=job_type
        )
        recurring = Assignment.objects.create(
            volunteer=self.test_volunteer.volunteer,
            job=job,
            day_of_week=date_to_day_of_month(future_date).day_of_week,
            week_of_month=date_to_day_of_month(future_date).week_of_month,
        )
        response = self.client.get("/volunteer/my_jobs/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Open Job 1")

        data = {
            "job_or_sub_pk": recurring.pk,
            "job_is_sub": "false",
            "job_date": datetime.datetime.strftime(future_date, "%b. %d, %Y"),
        }

        response = self.client.post(
            "/volunteer/request_substitute/", data, follow=True)
        self.assertEqual(response.status_code, 200)

        # make sure it's not in my jobs anymore
        response = self.client.get("/volunteer/my_jobs/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Test Open Job 1")

        # make sure it is in open jobs
        response = self.client.get("/volunteer/open_jobs/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(Substitution.objects.filter(volunteer=None)) > 0)
        self.assertContains(response, "Test Open Job 1")

    def test_take_sub_get_request(self):
        """ This test ensures you get redirected if you try to take a substitution via GET request."""
        __author__ = "Nate Strawser"
        response = self.client.get("/volunteer/take_substitution/")
        self.assertEqual(response.status_code, 302)

    @freeze_time("2020-03-15")
    def test_take_substitution(self):
        """
        This test requests a substitution, then requests to fill that substitution.
        It ensures the job reappears under the My Jobs page.
        """
        __author__ = "Nate Strawser"
        future_date = datetime.date(2020, 3, 25)  # some "future" date
        job_type = JobType.objects.create(name="test_type")
        job = Job.objects.create(
            name="Test Sub", num_vols_required=1, job_type=job_type
        )
        recurring = Assignment.objects.create(
            volunteer=self.test_volunteer.volunteer,
            job=job,
            day_of_week=date_to_day_of_month(future_date).day_of_week,
            week_of_month=date_to_day_of_month(future_date).week_of_month,
        )
        response = self.client.get("/volunteer/my_jobs/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Sub")

        data = {
            "job_or_sub_pk": recurring.pk,
            "job_is_sub": "false",
            "job_date": datetime.datetime.strftime(future_date, "%b. %d, %Y"),
        }

        # make sure it's in My Jobs to start with
        response = self.client.get("/volunteer/my_jobs/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Sub")

        # request the substitute
        response = self.client.post(
            "/volunteer/request_substitute/", data, follow=True)
        self.assertEqual(response.status_code, 200)

        # make sure it's no longer under My Jobs
        response = self.client.get("/volunteer/my_jobs/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Test Sub")

        data = {
            "pk": Substitution.objects.filter(
                assignment=recurring,
                date=future_date)[0].pk}

        # take the substitution back
        response = self.client.post(
            "/volunteer/take_substitution/", data, follow=True)
        self.assertEqual(response.status_code, 200)

        # make sure it's in My Jobs again
        response = self.client.get("/volunteer/my_jobs/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Sub")

    def test_invalid_sub(self):
        """ Make sure it doesn't crash if you take an invalid substitution. """
        __author__ = "Nate Strawser"
        data = {
            "pk": -1,
        }

        response = self.client.post(
            "/volunteer/take_substitution/", data, follow=True)
        self.assertEqual(response.status_code, 200)


class TestProfile(TestCase):
    def setUp(self):
        self.client = Client()
        self.test_volunteer = User.objects.get_or_create(
            username="test_request_user",
            password="password",
            email="admin@admin.com",
            is_staff=False,
        )[0]
        self.client.force_login(self.test_volunteer)

    def test_profile_path(self):
        """ This test ensures that the profile page returns a 200 status code """
        __author__ = "Nate Strawser"
        response = self.client.get("/volunteer/view_profile/")
        self.assertEqual(response.status_code, 200)

    def test_incorrect_path_fails(self):
        """ This test ensures that going to the incorrect page returns a 404 """
        __author__ = "Nate Strawser"
        response = self.client.get("/volunteer/profile/")
        self.assertEqual(response.status_code, 404)

    def test_profile_info_correct(self):
        """ This test ensures that the username, org, and cell phone all display properly on the page """
        __author__ = "Nate Strawser"
        response = self.client.get("/volunteer/view_profile/")
        self.assertContains(response, self.test_volunteer.username)
        self.assertContains(
            response, self.test_volunteer.volunteer.organization)
        self.assertContains(response, self.test_volunteer.volunteer.cell_phone)

    def test_contains_proper_fields(self):
        """ This test ensures that all of the fields that should be on the profile page are on there """
        __author__ = "Nate Strawser"
        fields = [
            "Username",
            "Organization",
            "Address",
            "Home Phone",
            "Cell",
            "Work Phone",
            "Birthdate",
            "Join Date",
        ]
        response = self.client.get("/volunteer/view_profile/")
        for field in fields:
            self.assertContains(response, field)
