#import core libs
from django.shortcuts import get_object_or_404
from django.http import HttpResponseBadRequest, HttpResponseNotAllowed
from django.db.models import Q
from datetime import date,datetime
from interfaces.recurrence import date_to_day_of_month

#models
from models.models import Assignment, Customer, ManagerAnnouncement, Route, Run
from . import serializers

#import dj-rest-auth methods
from rest_framework.response import Response

from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.views import APIView


class MissingDeliveryFeedback(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, routeId):
        date_object = date.today()
        date_string=date_object.strftime("%Y-%m-%d")
        route = get_object_or_404(Route.objects.filter(id=routeId))
        customers_on_run = Run.objects.filter(customer__route=route).filter(run_date=date_string).count()
        if customers_on_run == 0:
            customers_on_route = Customer.objects.filter(route=route) 
            for customer in customers_on_route:
                if customer.receives_meal_on_date(date_object):
                    Run.objects.create(customer=customer, run_date=date_string)
        customers_on_run_without_feedback = Run.objects.filter(customer__route=route).filter(run_date=date_string)

        serializer = serializers.RunSerializer(customers_on_run_without_feedback, many=True)

        return Response(serializer.data)

class ListAnnouncement(APIView):
    """
    Returns all annoucements.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            queryset = ManagerAnnouncement.objects.all()
            serializer = serializers.AnnouncementSerializer(queryset, many=True)

            return Response(serializer.data)
        except:
            return HttpResponseBadRequest()

class RouteOverview(APIView):
    """returns a route overview includes the route id and name along 
    with all the customers that should be getting a meal and their address.
    checks the volunteer is assigned to the route"""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, routeId, input_date):
        date_object = datetime.strptime(input_date, '%Y-%m-%d')
        dom = date_to_day_of_month(date_object)
        # used to get normal route, shuttle or packer assignments, this will also get subs if the volunteer has volunteered to sub for a job
        normalAssignments = Assignment.objects.filter((Q(
            job_id=routeId, 
            volunteer=self.request.user.volunteer, 
            day_of_week=dom.day_of_week, 
            week_of_month=dom.week_of_month) & ~Q(substitution__assignment__job_id=routeId, substitution__date=date_object) ) | Q(
                substitution__volunteer=self.request.user.volunteer, 
                substitution__assignment__job_id=routeId, 
                substitution__date=date_object))
        # this gets a bonus route assignment if the volunteer is assigned to it
        bonusPantryAssignments = Assignment.objects.filter(job_id= routeId, volunteer=self.request.user.volunteer, day_of_week=None, week_of_month=None)

        assignment = get_object_or_404(normalAssignments.union(bonusPantryAssignments))

        # check bonus route will run on the provided day, return 404 if not
        if str(assignment.job.job_type) == 'Bonus Delivery':
            nextBonusDeliveryDate = assignment.job.recurrence.after(date_object, inc=True, dtstart= date_object)
            if nextBonusDeliveryDate != date_object:
                return HttpResponseNotFound()

        route = Route.objects.get(id=assignment.job.id)
        serializer = serializers.RouteOverviewSerializer(route, context=date_object)

        return Response(serializer.data)

#Return 401 on /api/v1/
def DenyBasePath(request):
    return HttpResponseNotAllowed(('POST','GET', 'PUT', 'OPTIONS'))

