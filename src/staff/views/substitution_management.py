"""
Views file for managing susbstitutions
"""

import datetime
from logging import getLogger

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render, reverse

from interfaces.recurrence import date_to_day_of_month
from meals.constants import OPEN_ROUTE
from models.models import Assignment, Job, Substitution, Volunteer
from staff.forms import CreateSubstitutionForm, EditSubstitutionForm, FutureDateRangeForm

log = getLogger(__name__)


@staff_member_required
def manage_substitutions(request):
    """
    view for managing substitutions
    will bring up all substitutions by day
    """
    # get all the substitutions in the DB from today on
    subs = Substitution.objects.filter(
        date__gte=datetime.date.today()).order_by(
        "date", "assignment__job")
    subs = list(subs)
    for sub in subs:
        sub.route_number = sub.assignment.job.get_route_number()

    return render(request, "manage-substitutions.html",
                  {"subs": subs, "open_job": OPEN_ROUTE})


@staff_member_required
def edit_substitution(request, pk):
    """
    :param pk: primary key of substitution object
    POST: update the object with new data
    else, load the page displaying the data for the substitution
    """
    sub_req = get_object_or_404(Substitution, pk=pk)
    form = EditSubstitutionForm(instance=sub_req)

    if request.method == "POST":
        form = EditSubstitutionForm(request.POST, instance=sub_req)
        if form.is_valid():
            form.save()  # save to Volunteer model
            return HttpResponseRedirect(reverse("staff:manage_substitutions"))

    context = {
        "form": form,
        "assignment": sub_req.assignment,
        "date": sub_req.date,
        "sub_pk": sub_req.pk,
    }
    return render(request, "edit-substitution.html", context)


@staff_member_required
def create_substitution(request):
    """
    create a substitution object
    """
    form = CreateSubstitutionForm()
    if request.method == "POST":
        form = CreateSubstitutionForm(request.POST)
        if form.is_valid():
            return HttpResponseRedirect(reverse("staff:manage_substitutions"))
    date = datetime.date.today().strftime("%Y-%m-%d")
    return render(request, "create-substitution.html",
                  {"form": form, "date": date})


@staff_member_required
def remove_substitute(request, pk):
    """
    removes the substitute in the Substitution matching pk
    """
    sub_req = get_object_or_404(Substitution, pk=pk)
    sub_req.volunteer = None
    sub_req.save()
    return HttpResponseRedirect(reverse("staff:manage_substitutions"))


@staff_member_required
def delete_substitution(request, pk):
    """
    :param pk: primary key of substitution object
    delete the row corresponding to the primary key,
    404 if the item isn't found
    redirect back to manage-substitutions
    """
    sub_req = get_object_or_404(Substitution, pk=pk)
    sub_req.delete()
    return HttpResponseRedirect(reverse("staff:manage_substitutions"))


@staff_member_required
def spawn_open_jobs(request):
    form = FutureDateRangeForm()
    if request.method == "POST":
        form = FutureDateRangeForm(request.POST)
        if form.is_valid():
            # grab dates
            begin_date = form.cleaned_data["begin_date"]
            end_date = form.cleaned_data["end_date"]
            # create open sub requests for every day in the range
            for i in range((end_date - begin_date).days + 1):
                day = begin_date + datetime.timedelta(days=i)
                day_of_month = date_to_day_of_month(day)
                open_assignments = Assignment.objects.filter(
                    volunteer=None,
                    day_of_week=day_of_month.day_of_week,
                    week_of_month=day_of_month.week_of_month,
                )
                for assignment in open_assignments:
                    # don't create duplicates
                    subs = Substitution.objects.filter(
                        assignment=assignment, date=day)
                    if not subs.exists():
                        Substitution.objects.create(
                            assignment=assignment, date=day, volunteer=None,
                        )

            return HttpResponseRedirect(reverse("staff:manage_substitutions"))
    date = datetime.date.today().strftime("%Y-%m-%d")
    return render(request, "spawn-open-jobs.html",
                  {"form": form, "date": date})


@staff_member_required
def async_parse_assignment(request, date, job_pk):
    """
    :param date: date formatted YYYY-MM-DD
    :param job_pk: primary key of job object
    uses data to find assignment object and return data to
    the client and populate the form in real time
    Also checks to see if a substition for the job on
    the date exists already
    """
    try:
        date = datetime.datetime.strptime(date, "%Y-%m-%d")
        job = Job.objects.get(pk=job_pk)
    except (ValueError, Job.DoesNotExist):
        return JsonResponse({"status": "error"})

    response = {"status": "success", "vols": [], "sub_count": []}

    day_in_month = date_to_day_of_month(date)

    assignments = list(
        Assignment.objects.filter(
            day_of_week=day_in_month.day_of_week,
            week_of_month=day_in_month.week_of_month,
            job=job,
        )
    )

    # loop over assignments and populate the json
    for assignment in assignments:
        if assignment.volunteer is None:
            response["vols"].append({"vol_name": OPEN_ROUTE, "vol_pk": ""})
        else:
            response["vols"].append(
                {"vol_name": str(assignment.volunteer), "vol_pk": assignment.volunteer.pk, }
            )

    # find substituion data
    # only need a count
    response["sub_count"] = Substitution.objects.filter(
        date=date, assignment__job=job).count()

    return JsonResponse(response)
