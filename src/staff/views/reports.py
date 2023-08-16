"""
Views file for reports
contains views for parsing forms
"""

import datetime
from logging import getLogger

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render, reverse

from meals.constants import REPORT_TYPES
from staff.forms import DateRangeForm, MonthForm, SingleDateForm

log = getLogger(__name__)


@staff_member_required
def date_range_form(request, report_type):
    """
    :param report_type: type of report, this will either be
    job overview or substitution report
    view for the job overview and substitution report
    form. User will fill out form with date pickers
    this will parse and redirect to proper report
    """
    # make sure the report type is valid
    if report_type in REPORT_TYPES:
        # validate the form data
        form = DateRangeForm()
        if request.method == "POST":
            form = DateRangeForm(request.POST)
            if form.is_valid():
                begin_date = form.cleaned_data["begin_date"]
                end_date = form.cleaned_data["end_date"]
                try:
                    # get these for the report url
                    begin_date = begin_date.strftime("%m-%d-%Y")
                    end_date = end_date.strftime("%m-%d-%Y")
                except ValueError:
                    # if this causes an error redirect back to the form
                    report_type = report_type.replace("-", " ")
                    report_type = report_type.title()
                    # necessary for the forms
                    date_reversed = datetime.date.today().strftime("%Y-%m-%d")
                    return render(
                        request,
                        "date-range-form.html",
                        {"report_type": report_type, "date_reversed": date_reversed},
                    )

                # everything worked, so generate the report
                report_type = report_type.replace("-", "_")
                return HttpResponseRedirect(
                    reverse(
                        "pdfs:{}".format(report_type),
                        args=[
                            begin_date,
                            end_date]))
        # not a post request
        report_type = report_type.replace("-", " ")
        report_type = report_type.title()
        date_reversed = datetime.date.today().strftime("%Y-%m-%d")
        # get data for front end and render
        return render(
            request,
            "date-range-form.html",
            {"report_type": report_type, "date_reversed": date_reversed, "form": form},
        )

    # invalid report type
    return HttpResponseRedirect(reverse("staff:index"))


@staff_member_required
def month_form(request, report_type):
    """
    :param report_type: type of report, this will either be
    client or volunteer birthday report
    """
    # make sure the report type is valid
    if report_type in REPORT_TYPES:
        # validate the form data
        if request.method == "POST":
            form = MonthForm(request.POST)
            if form.is_valid():
                month = form.cleaned_data["month"]

                # everything worked, so generate the report
                report_type = report_type.replace("-", "_")
                return HttpResponseRedirect(
                    reverse("pdfs:{}".format(report_type), args=[month])
                )
        else:
            # not a post request
            report_type = report_type.replace("-", " ")
            report_type = report_type.title()
            form = MonthForm()
            # get data for front end and render
            return render(request, "month-form.html",
                          {"report_type": report_type, "form": form}, )

    # if all else fails, keep this here for now
    return HttpResponseRedirect(reverse("staff:index"))


@staff_member_required
def single_date_form(request, report_type):
    """
    This is used for reports that only take in a single date (e.g. daily count report).
    :param report_type is a report in meals.constants.
    """
    # make sure the report type is valid
    if report_type in REPORT_TYPES:
        # validate the form data
        if request.method == "POST":
            form = SingleDateForm(request.POST)
            if form.is_valid():
                date_picked = form.cleaned_data["date_picked"]
                try:
                    # get these for the report url
                    date_picked = date_picked.strftime("%m-%d-%Y")
                except ValueError:
                    # if this causes an error redirect back to the form
                    report_type = report_type.replace("-", " ")
                    report_type = report_type.title()
                    # necessary for the forms
                    date_reversed = datetime.date.today().strftime("%Y-%m-%d")
                    return render(
                        request,
                        "single-date-form.html",
                        {"report_type": report_type, "date_reversed": date_reversed},
                    )

                # everything worked, so generate the report
                report_type = report_type.replace("-", "_")
                return HttpResponseRedirect(
                    reverse("pdfs:{}".format(report_type), args=[date_picked])
                )
        else:
            # not a post request
            report_type = report_type.replace("-", " ")
            report_type = report_type.title()
            date_reversed = datetime.date.today().strftime("%Y-%m-%d")
            # get data for front end and render
            return render(
                request,
                "single-date-form.html",
                {"report_type": report_type, "date_reversed": date_reversed},
            )

    # if all else fails, keep this here for now
    return HttpResponseRedirect(reverse("staff:index"))


@staff_member_required
def volunteer_join_date_report(request):
    return HttpResponseRedirect(reverse("pdfs:volunteer_join_date_report"))
