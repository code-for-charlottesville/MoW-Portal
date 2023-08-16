from datetime import date, timedelta, datetime
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token


from rest_framework.test import APITestCase
from rest_framework import status

from models.models import Assignment, Customer, JobType, Route, Run, Volunteer

import recurrence


class TestDeliveryFeedback(APITestCase):

    @classmethod    
    def setUpTestData(self):      
        self.date= date.today().strftime('%Y-%m-%d')
        print(self.date)
        myrule = recurrence.Rule(recurrence.DAILY)

        pattern = recurrence.Recurrence(
        dtstart=datetime(2020, 1, 2, 0, 0, 0),
        dtend=datetime(2030, 1, 3, 0, 0, 0),
        rrules=[myrule, ]
        )   

        job_type = JobType.objects.create(name='test_type')
        route = Route.objects.create(description='test_route', number='939', job_type=job_type)
        Customer.objects.create(first_name='sample', last_name='customer', address='123 fake st Sprinfield, MA 12345', active=True, birth_date='1901-02-03', route=route, meal_recurrence=pattern)
        Customer.objects.create(first_name='llama', last_name='duck', address='123 fake st Sprinfield, MA 12345', active=True, birth_date='1901-02-03', route=route, meal_recurrence=pattern)
        self.user = User.objects.create_user(username='llama', password='duck', email='test@test.com', is_staff=True, is_active=True)

    def setUp(self):
        authResponse = self.client.post('/api/v1/dj-rest-auth/login/', data={'username': 'llama', 'password': 'duck'}, format='json')
        token = authResponse.json()['key']
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)

    def test_entire_delivery_feedback_flow(self):
        response = self.client.get('/api/v1/missing-delivery-feedback-today/2')

        self.assertJSONEqual(response.content,'[{"customer": 1,"feedback_provided": false},{"customer": 2,"feedback_provided": false}]')

        bad_delivery_status = {
            "delivery_status": "ahh",
            'customer_status': "Needs follow up",
            'notes': "not good",
        }

        response = self.client.put(f'/api/v1/delivery-feedback/?route=2&run_date={self.date}&customer=1', bad_delivery_status, format='json')
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertJSONEqual(response.content, '{"delivery_status": ["delivery status not accepted"]}')        

        bad_customer_status = {
            "delivery_status": "Client answered",
            'customer_status': "ahh",
            'notes': "not good",
        }

        response = self.client.put(f'/api/v1/delivery-feedback/?route=2&run_date={self.date}&customer=1', bad_customer_status, format='json')
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertJSONEqual(response.content, '{"customer_status": ["customer status not accepted"]}')

        good = {
            "delivery_status": "Client answered",
            'customer_status': "Needs follow up",
            'notes': "not good",
        }

        response = self.client.put(f'/api/v1/delivery-feedback/?route=2&run_date={self.date}&customer=2', good, format='json')
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        response = self.client.get('/api/v1/missing-delivery-feedback-today/2')
        self.assertJSONEqual(response.content,'[{"customer": 1,"feedback_provided": false},{"customer": 2,"feedback_provided": true}]')
        


class TestRouteOverview(APITestCase):


    @classmethod
    def setUpTestData(self): 

        myrule = recurrence.Rule(recurrence.DAILY)

        self.pattern = recurrence.Recurrence(
        dtstart=datetime(2020, 1, 2, 0, 0, 0),
        dtend=datetime(2030, 1, 3, 0, 0, 0),
        rrules=[myrule, ]
        )   
        job_type = JobType.objects.create(name='test_type')
        self.route = Route.objects.create(name = 'test route name', description='test_route', number='939', job_type=job_type)
        Customer.objects.create(first_name='sample', last_name='customer', address='123 fake st Sprinfield, MA 12345', birth_date='1901-02-03', route=self.route, active=True)
        self.user = User.objects.create_user(username='llama2', password='duck', email='test@test.com', is_staff=True, is_active=True)
        self.vol = Volunteer.objects.get(user=self.user)
        Assignment.objects.create(volunteer= self.vol, job=self.route, day_of_week=3, week_of_month=4)

    def setUp(self):
        authResponse = self.client.post('/api/v1/dj-rest-auth/login/', data={'username': 'llama2', 'password': 'duck'}, format='json')

        token = authResponse.json()['key']
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)

        

    def testRouteOverview(self):
        """volunteer is assigned to route but no customer is receiving a meal"""
        response = self.client.get('/api/v1/route-overview/3/date/2022-04-27')
        customers = response.json()['customers']
        self.assertEqual(len(customers), 0)

        '''add a customer that is receiving a meal'''
        Customer.objects.create(first_name='llama', last_name='duck', address='123 fake st Sprinfield, MA 12345', birth_date='1901-02-03', route=self.route, meal_recurrence=self.pattern, active=True)

        '''customer receiving meal is assigned to route and a volunteer is assigned, the customer array length should be 1'''
        response = self.client.get('/api/v1/route-overview/3/date/2022-04-27')
        customers = response.json()['customers']
        self.assertEqual(len(customers), 1)

        '''the volunteer is not assigned to the route for the provided date'''
        response = self.client.get('/api/v1/route-overview/3/date/2022-04-28')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

