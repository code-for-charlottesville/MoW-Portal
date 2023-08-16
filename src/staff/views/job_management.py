"""
Views file for managing jobs
"""

import datetime
from dataclasses import dataclass, field
from logging import getLogger
from typing import List, Optional, Set
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render, reverse
from interfaces.recurrence import date_to_day_of_month, is_weekend
from meals.constants import OPEN_ROUTE, OPEN_SUBSTITUTION, ROUTE_TYPE_NAME, UNASSIGNED_JOB
from models.models import NO_FILTER_SENTINAL, Assignment, Job, JobType, Route, Substitution
from staff.forms import DateForm, JobForm, JobFormNoType, JobTypeForm, RouteForm, BonusDeliveryForm

log = getLogger(__name__)


@dataclass
class Person:
    name: str
    sub_pk: Optional[int]
    assignment_pk: int
    original: str
    email: Optional[str]
    volunteer_pk: Optional[int]


@dataclass
class JobStruct:
    job: Job
    route_number: Optional[int]
    todays_volunteers: List[Person] = field(default_factory=list)
    emails: Set[str] = field(default_factory=set)
    email_str = Optional[str]

    def __eq__(self, __o: object) -> bool:
        return self.job.id == __o.id


@dataclass
class JobTypeStruct:
    job_type: JobType
    jobs: List[JobStruct] = field(default_factory=list)
    emails: Set[str] = field(default_factory=set)
    email_str = Optional[str]

    def __eq__(self, __o: object) -> bool:
        return str(self.job_type.name) == str(__o.job_type.name)


@dataclass
class Date:
    date: datetime.date
    job_types: List[JobTypeStruct] = field(default_factory=list)
    emails: Set[str] = field(default_factory=set)
    email_str = Optional[str]

    def __eq__(self, __o: object) -> bool:
        return self.date == __o.date


def populate_structs(date_list, date, job):
    # add the date struct if it is not in the date_list
    d = Date(date)
    if d not in date_list:
        date_list.append(d)
    # find the index of the date in date_list
    dateIndexInList = date_list.index(d)
    # use the index to find the valid job types for the date struct
    jobTypesForDate = date_list[dateIndexInList].job_types
    # create a job type struct
    jts = JobTypeStruct(job.job_type)
    # add the job type if not in the list of job types for the given date
    if jts not in jobTypesForDate:
        jobTypesForDate.append(jts)
    # find the index for the job type
    jtsIndexInList = jobTypesForDate.index(jts)
    # get the list of jobs for the current job type
    jobTypeList = jobTypesForDate[jtsIndexInList].jobs
    # create the job struct
    jobStruct = JobStruct(job, route_number=job.get_route_number())
    # add the job to the list if not in list
    if job not in jobTypeList:
        jobTypeList.append(jobStruct)

    return jobTypeList[-1]


def actual_to_person(a):
    dom = date_to_day_of_month(a.date)
    assignment_pks = Assignment.objects.filter(
        volunteer=a.original,
        job=a.job,
        day_of_week=dom.day_of_week,
        week_of_month=dom.week_of_month,
    ).values_list("pk")
    if a.is_substitution:
        subs = list(
            Substitution.objects.filter(
                volunteer=a.volunteer, assignment__pk__in=assignment_pks,
            )
        )
        sub_pk = subs[0].pk
        ass_pk = subs[0].assignment.pk
    elif hasattr(a.job, 'route') and a.job.route.bonusRoute is not None:
        sub_pk = None
        ass_pk = Assignment.objects.filter(volunteer=a.original, job=a.job, day_of_week=None, week_of_month=None).values_list('pk')[0][0]
    else:
        sub_pk = None
        ass_pk = assignment_pks[0][0]
    if a.volunteer:
        name = str(a.volunteer)
    elif a.is_substitution:
        name = OPEN_SUBSTITUTION
    else:
        name = OPEN_ROUTE
    return Person(
        name=name,
        sub_pk=sub_pk,
        assignment_pk=ass_pk,
        original=str(a.original) if a.original else OPEN_ROUTE,
        email=a.volunteer.user.email if a.volunteer else None,
        volunteer_pk=a.volunteer.pk if a.volunteer else None,
    )


def actuals_to_display(
    start_date,
    end_date=None,
    *,
    volunteer=NO_FILTER_SENTINAL,
    original=NO_FILTER_SENTINAL,
    job=NO_FILTER_SENTINAL,
    exclude_unfilled=False,
    **kwargs,  # support future changes to actuals() interface
):
    actuals = Assignment.actuals(
        start_date,
        end_date,
        volunteer=volunteer,
        original=original,
        job=job,
        order_by=("date", "job", "volunteer"),  # must be totally sorted
        exclude_unfilled=exclude_unfilled,
        **kwargs,
    )
    actuals = list(actuals)
    all_jobs= Job.objects.all()

    jobs_index = 0

    dates = []
    for i, a in enumerate(actuals):

        # insert unassigned jobs from last day
        while jobs_index < len(all_jobs) and a.job != all_jobs[jobs_index]:
            job_struct = populate_structs(
                        dates, actuals[max(i - 1, 0)].date, all_jobs[jobs_index]
                    )
            jobs_index += 1

        # insert unassigned jobs from today
        if jobs_index == len(all_jobs):
            jobs_index = 0
        while a.job != all_jobs[jobs_index]:
            job_struct = populate_structs(dates, a.date, all_jobs[jobs_index])
            jobs_index += 1

        # insert this job and get the volunteer list
        todays_volunteers = populate_structs(
            dates, a.date, a.job).todays_volunteers

        # add this volunteer's information
        todays_volunteers.append(actual_to_person(a))
        if a.volunteer and a.volunteer.user.email:
            # needed to ensure the volunteer data is put into the correct location
            d = Date(a.date)
            dIndex = dates.index(d)
            jt = JobTypeStruct(a.job.job_type)
            jtIndex = dates[dIndex].job_types.index(jt)
            jIndex = dates[dIndex].job_types[jtIndex].jobs.index(a.job)
            dates[dIndex].job_types[jtIndex].jobs[jIndex].emails.add(a.volunteer.user.email)
            dates[dIndex].job_types[jtIndex].emails.add(a.volunteer.user.email)
            dates[dIndex].emails.add(a.volunteer.user.email)

    # insert unfilled jobs to the end
    if "a" in locals():
        for ji in range(jobs_index, len(all_jobs)):
            job_struct = populate_structs(dates, a.date, all_jobs[ji])

    # comma-seperate emails
    for d in dates:
        d.email_str = ";".join(d.emails)
        for jt in d.job_types:
            jt.email_str = ";".join(jt.emails)
            for j in jt.jobs:
                j.email_str = ";".join(j.emails)
    return dates


@staff_member_required
def manage_jobs(request, date=None):
    """
    Display all of the jobs
    """

    # HANDLE DATES
    if date is None:
        date_str = datetime.date.today().strftime("%m-%d-%Y")
        return HttpResponseRedirect(
            reverse(
                "staff:manage_jobs",
                args=[date_str]))

    # convert the url to a datetime
    try:
        date = datetime.datetime.strptime(date, "%m-%d-%Y")
    except ValueError:
        date_str = datetime.date.today().strftime("%m-%d-%Y")
        return HttpResponseRedirect(
            reverse(
                "staff:manage_jobs",
                args=[date_str]))
    date = datetime.date(year=date.year, month=date.month, day=date.day)
    if is_weekend(date):
        days_to_add = 8 - date.isoweekday()
        next_weekday = date + datetime.timedelta(days=days_to_add)
        date_str = next_weekday.strftime("%m-%d-%Y")
        return HttpResponseRedirect(
            reverse(
                "staff:manage_jobs",
                args=[date_str]))

    dates = actuals_to_display(date)
    if not dates:
        job_types_struct = JobTypeStruct(
            job_type=JobType(name="No Data Found"),)
        job_types_struct.email_str = ""
    else:
        job_types_struct = dates[0]
    return render(
        request,
        "manage-jobs.html",
        {
            "job_types_struct": job_types_struct,
            "open_route": OPEN_ROUTE,
            "open_substitution": OPEN_SUBSTITUTION,
            "unassigned_job": UNASSIGNED_JOB,
            "date_display": date.strftime("%A, %B %d, %Y"),
            "url_date": date.strftime("%m-%d-%Y"),
            "date_picker_date": date.strftime("%Y-%m-%d"),
            "routeNames": ["Route", "Bonus Route"]
        },
    )


@staff_member_required
def create_job(request):
    """
    determine if its a route or a regular job
    and create accordingly
    """
    # this form is used when the create job page is initilly displayed, creates a select element with the possible job types
    jobTypeForm = JobTypeForm()

    # get the pk for the route and bonus route job type, this is used in the logic to determine which forms are displayed on the create-jobs page
    route_type_pk = str(JobType.objects.get_or_create(name="Route")[0].pk)
    bonusDeliveryPk = str(JobType.objects.get_or_create(name="Bonus Delivery")[0].pk)
    # get the next_route_number to populate the number field in the route and bonus route forms

    try:
        next_route_number = Route.objects.all().order_by(
            "-number")[0].number + 1
    except IndexError:
        # no routes in database
        next_route_number = 1
    # create forms
    job_form = JobForm()
    route_form = RouteForm(initial={"number": next_route_number})
    bonusDeliveryForm = BonusDeliveryForm(initial={"number": next_route_number})
    # create route, bonus route or job entites based on the job type value
    job_type=0
    if request.method == "POST":
        # create a route
        job_type=request.POST.get('job_type')
        if job_type == route_type_pk:
            route_form = RouteForm(request.POST)
            if route_form.is_valid():
                route_form.save()
                return HttpResponseRedirect(reverse("staff:manage_jobs"))
        # create a bonus route
        if job_type == bonusDeliveryPk:
            bonusDeliveryForm = BonusDeliveryForm(request.POST)
            if bonusDeliveryForm.is_valid():
                bonusDeliveryForm.save()
                return HttpResponseRedirect(reverse("staff:manage_jobs"))
        else:
            # create a regular job
            job_form = JobForm(request.POST)
            if job_form.is_valid():
                job_form.save()
                return HttpResponseRedirect(reverse("staff:manage_jobs"))

    return render(
        request,
        "create-job.html",
        {
            "job_form": job_form,
            "route_form": route_form,
            "bonusDeliveryForm": bonusDeliveryForm,
            "next_route_number": next_route_number,
            "route_type_pk": route_type_pk,
            "bonusDeliveryPk": bonusDeliveryPk,
            "jobTypeForm": jobTypeForm,
            "job_type": job_type
        },
    )


@staff_member_required
def edit_job(request, pk):
    """
    :param pk: job's primary key (int)
    if pk is None, it will create a new job
    Allows staff to edit a job's details
    THIS IS FOR NON-ROUTE. FOR ROUTES,
    go to view_route in Routes app
    """
    job_instance = get_object_or_404(Job, pk=pk)
    job_type = job_instance.job_type.name.title()
    form = JobFormNoType(instance=job_instance)
    # get instance of this form
    # using no type form, won't allow change of job type

    if request.method == "POST":
        # validate and save the changes
        form = JobFormNoType(request.POST, instance=job_instance)

        if form.is_valid():
            # valid so save
            form.save()
            return HttpResponseRedirect(reverse("staff:manage_jobs"))

    return render(
        request,
        "edit-job.html",
        {
            "form": form,
            "job_pk": pk,
            "job_type": job_type,
            "emails": get_emails_by_job(job_instance),
            "url": reverse("staff:manage_assignments_table", args=[pk]),
        },
    )


@staff_member_required
def delete_job(request, pk):
    """
    :param pk:
    delete the job with the specified pk
    """
    job = get_object_or_404(Job, pk=pk)
    # get the job and delete it
    # assignments taken care of in models
    job.delete()
    return HttpResponseRedirect(reverse("staff:manage_jobs"))


@staff_member_required
def manage_open_job(request, assignment_pk, date):
    """
    this is the link to create a substitution request from
    an open job displayed on the manage-jobs page
    """
    # handle the date
    try:
        date_as_datetime = datetime.datetime.strptime(date, "%m-%d-%Y")
    except ValueError:
        # redirect to today if not valid
        date_str = datetime.date.today().strftime("%m-%d-%Y")
        return HttpResponseRedirect(
            reverse(
                "staff:manage_jobs",
                args=[date_str]))

    # get the assignment
    assignment = get_object_or_404(Assignment, pk=assignment_pk)

    # make sure that this assignment is actually an open job
    if assignment.volunteer is None:
        # create open substitution request, do nothing if it exists already
        Substitution.objects.get_or_create(
            volunteer=None, assignment=assignment, date=date_as_datetime
        )

    return HttpResponseRedirect(reverse("staff:manage_jobs", args=[date]))


@staff_member_required
def parse_date_form(request):
    """
    This handles the form on the manage-job page
    it takes in the data and redirects as needed
    """
    date_str = datetime.date.today().strftime("%m-%d-%Y")
    if request.method == "POST":
        form = DateForm(request.POST)
        if form.is_valid():
            # set the date and redirect to it
            date = form.cleaned_data["date"]
            try:
                date_str = date.strftime("%m-%d-%Y")
            except ValueError:
                # handled
                pass

    return HttpResponseRedirect(reverse("staff:manage_jobs", args=[date_str]))


class Emails:
    def __init__(self, assigned_emails, sub_emails):
        self.assigned_emails = ",".join(set(assigned_emails))
        self.sub_emails = ",".join(set(sub_emails))
        self.all_emails = ",".join(set(sub_emails + assigned_emails))


def get_emails_by_job(job_name):
    """
    get the list of emails for everyone who has
    any sort of assignment for a job
    return assigned_emails, sub_emails, and all_emails
    """
    # get job
    job = Job.objects.get(name=job_name)
    # get the emails of anyone ever assigned
    assignments = Assignment.objects.filter(job=job)
    assigned_emails = []
    for assignment in assignments:
        if assignment.volunteer:
            email = assignment.volunteer.user.email
            if email:
                assigned_emails.append(email)

    # get the emails of anyone who may be substituting
    substitutions = Substitution.objects.filter(
        assignment__job=job, date__gte=datetime.date.today()
    )
    sub_emails = []
    for sub in substitutions:
        # get the email, if its not in the ones we
        # got in the assignments, append it
        if sub.volunteer:
            email = sub.volunteer.user.email
            if email:
                sub_emails.append(email)

    # join with comma
    # return all of the emails
    return Emails(assigned_emails, sub_emails)
