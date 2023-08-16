from django.http import HttpResponseNotFound, HttpResponseBadRequest, HttpResponseNotAllowed
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from interfaces.recurrence import DayOfMonth, day_of_month_to_date

from models.models import Assignment, Substitution
import api.serializers as serializers

from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.views import APIView

class MyJobsViewSet(APIView):

    class Job():
        def __init__(self, jobId, routeNumber, jobName, jobType, volunteerId, date, isSub):
            self.routeNumber = routeNumber
            self.jobId = jobId
            self.jobName = jobName
            self.jobType = jobType
            self.volunteerId = volunteerId
            self.date = date
            self.isSub = isSub
        def __str__(self):
            text = '\nroute number=' + str(self.routeNumber)
            text += '\njob id=' + str(self.jobId)
            text += '\njob name=' + self.jobName
            text += '\njob type=' + self.jobType
            text += '\ndate= ' + str(self.date)
            text += '\n'
            return text


    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Returns at least the next 5 jobs. this can vary because it includes all jobs for the data of the last element
        Response is a list of objects containing route_number, job_name, job_type, volunteer_id, date_yyyy_mm_dd
        """

        # get all assignments for a volunteer
        try:
            assignments = Assignment.objects.filter(volunteer=self.request.user.volunteer)

            my_jobs_data = []

            # some setup for the while loop
            current_date = datetime(date.today().year, date.today().month, date.today().day)
            bonusDeliveryJobs = []
            assignments = list(assignments)
            # handle assignments for bonus routes
            for assignment in assignments:
                if str(assignment.job.job_type) == 'Bonus Delivery':
                    assignments.remove(assignment)
                    bonusRouteJobDays = assignment.job.recurrence.between(current_date, current_date + relativedelta(months = 1), dtstart=current_date, inc=True)
                    for jobDay in bonusRouteJobDays:
                        bonusDeliveryJobs.append(self.Job(assignment.job.get_route_number(), assignment.job.id, assignment.job.name, assignment.job.job_type.name, assignment.volunteer.user.id, date(year = jobDay.year, month= jobDay.month, day = jobDay.day), False))

            # get the date of all assignments left for the month, if there is less then 15, this number is kinda arbitrary, increment the month and if needed the year
            # 15 is used because we need to be sure we include all jobs on a date in the response
            if len(assignments) > 0:
                while len(my_jobs_data) < 15 and (current_date - datetime.now() ).days < 90:
                    for assignment in assignments:
                        if assignment.day_of_week is not None and assignment.week_of_month is not None:
                            day_of_month = DayOfMonth(
                                day_of_week = assignment.day_of_week,
                                week_of_month = assignment.week_of_month
                            )
                            date_of_job_this_month = day_of_month_to_date(day_of_month, current_date.month, current_date.year)
                                # don't add dates that already happened
                            if date_of_job_this_month is None or date_of_job_this_month < date.today():
                                continue

                            job_in_sub_list = Substitution.objects.filter(assignment=assignment, date=date_of_job_this_month) # search for a substituion with the same assignment and date

                            if len(job_in_sub_list) == 0: # if a substitution is found with the same assignment and date, it will not be added to the list
                                my_jobs_data.append(self.Job(assignment.job.get_route_number(), assignment.job.id, assignment.job.name, assignment.job.job_type.name, assignment.volunteer.user.id, date_of_job_this_month, False))

                    current_date += relativedelta(months=1)
            # sort the list to ensure the soonest jobs are first
            my_jobs_data.sort(key=lambda r: r.date)

            #  get all the subs the volunteer is volunteering for using the min and max date already in the list as part of the query
            # if there are no assignments, retrieve starting today and 1 month out
            if len(my_jobs_data) > 0:
                end_date = my_jobs_data[-1].date
            else:
                end_date = date.today() + relativedelta(months=6)

            substitutions = Substitution.objects.filter(volunteer=self.request.user.volunteer, date__gte=date.today(), date__lte=end_date)
            # # if there are any subs add them to the my_jobs_data list
            if len(substitutions) > 0:
                job_subs = []
                for sub in substitutions:
                    if len(job_subs) < 10:
                        job_subs.append(self.Job(sub.assignment.job.get_route_number(), sub.assignment.job.id, sub.assignment.job.name, sub.assignment.job.job_type.name, sub.volunteer.user.id, sub.date, True))
                my_jobs_data.extend(job_subs)

            # sort the list again
            my_jobs_data.extend(bonusDeliveryJobs)
            my_jobs_data.sort(key=lambda r: r.date)

            #  we want to be sure to include all jobs for the day a volunteer is volunteering but want to keep the list some what short
            #  so if my_jobs_data is greater then 5 but there is multiple assignments on that day include them in the response
            #  remove any dates greater then the date of the fifth element

            count = len(my_jobs_data)
            while count >= 5:
                if my_jobs_data[4].date < my_jobs_data[-1].date:
                    del my_jobs_data[-1]
                count -= 1

            serializer = serializers.MyJobSerializer(my_jobs_data, many=True)

            return Response(serializer.data)
        except:
            return HttpResponseBadRequest()

