"""
Views for volunteers
"""
import datetime
from logging import getLogger

from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from accounts.forms import SignUpForm, VolunteerForm
from interfaces.recurrence import day_of_month_to_date
from meals.constants import OPEN_ROUTE
from models.models import Assignment, Job, ManagerAnnouncement, Route, Substitution, Volunteer
from staff.views.index import query_substitutions_table

log = getLogger(__name__)


@login_required
def index(request):
    """
    Welcome page
    """
    alert_query = ManagerAnnouncement.objects.filter(
        display_until__gte=datetime.date.today())
    sub_day_dict = query_substitutions_table(7, None)
    return render(request, "welcome-volunteer.html",
                  {"subs": sub_day_dict, "alerts": alert_query})


@login_required
def my_jobs(request):
    """
    My Jobs Page
    This page shows all the recurring jobs associated with a given volunteer, as well as jobs they are substitutes for.

    TODO: enforce 48 hour check on backend (already enforced on front end)
    """

    # get a list of all the substitutions that happen for this volunteer in
    # the future
    jobs_list = Assignment.objects.filter(volunteer=request.user.volunteer)
    substitutions_list = Substitution.objects.filter(
        volunteer=request.user.volunteer, date__gte=datetime.date.today()
    )

    my_jobs_and_substitutions = []
    # format: [job/substitution, date, is_substitution: bool, is_route,
    # route_url]

    # are we viewing the page for a different month than the current month?
    try:
        month_offset = int(request.GET.get("month"))
    except (ValueError, TypeError):
        month_offset = 0

    # add time to account for months in the future
    query_date = datetime.datetime.now() + relativedelta(months=+month_offset)

    for sub in substitutions_list:
        if sub.date.month != query_date.month:
            continue  # only include substitutions that occur in the month that we're viewing
        route_number = sub.assignment.job.get_route_number()
        my_jobs_and_substitutions.append(
            (
                sub.assignment,
                sub.date.strftime("%b. %d, %Y"),
                sub.date.strftime("%m-%d-%Y"),
                True,
                route_number != -1,
                sub.pk,
            )
        )

    for assignment in jobs_list:
        date_of_job_this_month = day_of_month_to_date(
            assignment.to_day_of_month(), query_date.month, query_date.year,
        )

        # don't add dates that already happened
        if date_of_job_this_month is None or date_of_job_this_month < datetime.date.today():
            continue

        try:
            sub = Substitution.objects.get(
                assignment=assignment, date=date_of_job_this_month)
        except Substitution.DoesNotExist as e:  # don't display jobs you've requested a substitute for
            route_number = assignment.job.get_route_number()
            my_jobs_and_substitutions.append(
                (
                    assignment,
                    date_of_job_this_month.strftime("%b. %d, %Y"),
                    date_of_job_this_month.strftime("%m-%d-%Y"),
                    False,
                    route_number != -1,
                    assignment.pk,
                )
            )

    # sort based on ascending dates; the 1 represents the position of the date
    # in the tuple
    my_jobs_and_substitutions = sorted(
        my_jobs_and_substitutions, key=lambda x: x[1])

    return render(
        request,
        "volunteer_jobs.html",
        {
            "my_jobs": my_jobs_and_substitutions,
            "month": query_date.strftime("%B"),
            "year": query_date.year,
            "table_length": len(my_jobs_and_substitutions),
        },
    )


@login_required
def request_substitute(request):
    """
    This method takes a POST request with a specific date job primary key and creates
    a substitution for the given user for that date and job,
    then redirects back to the my_jobs page
    """
    if request.method == "POST":
        sub_date_str = request.POST.get("job_date")
        is_sub = request.POST.get("job_is_sub")
        sub_date = datetime.datetime.strptime(
            sub_date_str, "%b. %d, %Y").date()

        if is_sub.lower() == "true":
            # if we're processing a substitution for a job that you're supposed
            # to be the substitute for
            previous_substitution = get_object_or_404(
                Substitution,
                pk=request.POST.get(
                    "job_or_sub_pk"
                ),  # TODO: refactor this to assignment_or_sub_pk
            )
            # delete the current substitution record if you're requesting a
            # substitute for something you substituted for
            previous_substitution.delete()
            sub = Substitution(
                volunteer=None,
                assignment=previous_substitution.assignment,
                date=sub_date,
            )
        else:
            ass_pk = request.POST.get("job_or_sub_pk")
            assignment = get_object_or_404(Assignment, pk=ass_pk)
            sub = Substitution(
                volunteer=None,
                assignment=assignment,
                date=sub_date)
        sub.save()

    return HttpResponseRedirect(reverse("volunteers:my_jobs"))


@login_required
def open_jobs(request):
    """
    This function shows all open substitutions that a volunteer can take.
    """
    subs = Substitution.objects.filter(
        volunteer=None, date__gte=datetime.date.today()
    ).order_by("date")
    open_jobs = []

    for sub in subs:
        open_jobs.append(
            (
                sub.assignment.job,
                sub.date,
                sub.date.strftime("%m-%d-%Y"),
                sub.assignment.job.get_route_number() != -1,
                sub.pk,
            )
        )
    context = {"subs": open_jobs}

    return render(request, "volunteer-open-jobs.html", context)


@login_required
def take_substitution(request):
    """
    This function assigns a volunteer to a given job.
    """
    if request.method == "POST":
        try:
            sub = get_object_or_404(Substitution, pk=request.POST.get("pk"))
            if sub.assignment.volunteer == request.user.volunteer:
                # might as well say it is not via substitutions in this case
                sub.delete()
            else:
                sub.volunteer = request.user.volunteer
                sub.save()
        except BaseException:
            log.error("Attempting to take substitution that does not exist.")

        return HttpResponseRedirect(reverse("volunteers:open_jobs"))

    else:
        log.info(
            "Attempting to take substitution with {} method. Only POST allowed.".format(
                request.method))
        return HttpResponseRedirect(reverse("volunteers:my_jobs"))


@login_required
def view_profile(request):
    volunteer = request.user.volunteer
    user_form = SignUpForm(request.GET)
    vol_form = VolunteerForm(request.GET)
    context = {
        "volunteer": volunteer,
        "user_form": user_form,
        "vol_form": vol_form}
    return render(request, "volunteer-profile.html", context)
