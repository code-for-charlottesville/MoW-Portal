from django.test import Client
from django.contrib.auth.models import User
from interfaces.recurrence import date_to_day_of_month, day_of_month_to_date
import datetime
import re

from rest_framework.test import APITestCase
from rest_framework import status

from models.models import JobType, Job, Assignment, Substitution, Volunteer, Route


class TestMyJobs(APITestCase):

    @classmethod
    def setUpTestData(self):
        self.today = datetime.date.today()

        job_type = JobType.objects.create(name='test_type')
        # job = Job.objects.create(name='test job name')
        self.route = Route.objects.create(name='test route name', description='test_route', number=1, job_type=job_type)
        self.user = User.objects.create_user(username='test_user', password='test_password', email='test@test.com', is_staff=True, is_active=True)
        self.vol = Volunteer.objects.get(user=self.user)
        Assignment.objects.create(
            volunteer= self.vol,
            job=self.route,
            day_of_week=date_to_day_of_month(
                self.today).day_of_week,
            week_of_month=date_to_day_of_month(
                self.today).week_of_month
        )

    def setUp(self):
        authResponse = self.client.post('/api/v1/dj-rest-auth/login/', data={'username': 'test_user', 'password': 'test_password'}, format='json')

        token = authResponse.json()['key']
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)

    def test_my_jobs_assignment(self):
        """ This test creates a job and recurring assignment for that volunteer and ensures that job exists """

        response = self.client.get('/api/v1/my-jobs/')
        jobs_list = response.json()
        jobs_content = str(response.content, encoding='utf8')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(jobs_list), 5)

        first_job_as_string = jobs_content.split(',{')[0].split('[')[1] # split out the first object to compare it with an expected object, had trouble doing this converting the regular object to a utf8 string, but then AssertJSONEqual didn't like a normal string
        print(first_job_as_string)
        today_YYYY_MM_DD = self.today.strftime('%Y-%m-%d')
        self.assertJSONEqual(first_job_as_string, {'routeNumber': '1', 'jobId': 1, 'jobName': 'test route name', 'jobType': 'test_type', 'volunteerId': self.vol.id, 'date_yyyy_mm_dd': today_YYYY_MM_DD, 'isSub': False})