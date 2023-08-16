"""
Views file for assignment management
"""

from logging import getLogger

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, reverse

from accounts.forms import VolunteerForm
from interfaces.recurrence import (
    abbreviated_days_of_week,
    abbreviated_weeks_of_month,
    days_of_month_field_names,
    days_of_month_tuples,
    days_of_week,
    end_of_week_field_names,
    start_of_week_field_names,
    weeks_of_month,
)
from meals.constants import OPEN_ROUTE
from models.models import Assignment, Job, Volunteer
from staff.forms import CreateAssignmentForm, EditMultipleAssignmentsForm

log = getLogger(__name__)


@staff_member_required
def create_recurrence(request):
    """
    create a new assignment
    """
    form = CreateAssignmentForm()
    # order the jobs in the dropdown
    if request.method == "POST":
        # validate and save
        form = CreateAssignmentForm(request.POST)
        if form.is_valid():
            return HttpResponseRedirect("/staff/manage-assignments/")

    return render(
        request,
        "create-assignment.html",
        {
            "form": form,
            "start_of_week_field_names": start_of_week_field_names,
            "end_of_week_field_names": end_of_week_field_names,
        },
    )


class Row:
    """
    class used to display each row in the table
    contains various assignment information
    and a list of assignment display
    """

    def __init__(self, assignment):
        self.volunteer = assignment.volunteer
        self.job = assignment.job
        self.route_number = assignment.job.get_route_number()
        self.visible_assignments = []
        self.hidden_assignments = [
            SingleDayAssignment(
                assignment.week_of_month,
                assignment.day_of_week)]

    def __lt__(self, other_row):
        """
        used with sorted is called
        this allows the route to all get displayed first by route number
        then all other jobs by alphabetical
        """
        if (self.route_number != -1 and other_row.route_number != -1) and (
            self.route_number != other_row.route_number
        ):
            # both are routes but not the same route
            return self.route_number < other_row.route_number
        elif self.route_number == -1 and other_row.route_number != -1:
            # one is not a route
            # routes will get priority in default sort
            return False
        elif self.route_number != -1 and other_row.route_number == -1:
            # one is not a route
            # routes will get priority in default sort
            return True
        elif self.job.job_type.name != other_row.job.job_type.name:
            # this will allow for the packers and shuttles to be separated
            return self.job.job_type.name < other_row.job.job_type.name
        elif self.job.name != other_row.job.name:
            # they are not the same job
            return self.job.name < other_row.job.name
        else:
            if self.volunteer and other_row.volunteer:
                self_name = f"{self.volunteer.user.first_name.lower()} {self.volunteer.user.last_name.lower()}"
                other_row_name = f"{other_row.volunteer.user.first_name.lower()} {other_row.volunteer.user.last_name.lower()}"
                return self_name < other_row_name
            elif self.volunteer:
                # one will display as open route
                self_name = f"{self.volunteer.user.first_name.lower()} {self.volunteer.user.last_name.lower()}"
                return self_name < OPEN_ROUTE.lower()
            else:
                # other_row.volunteer is not None
                # one will display as open route
                other_row_name = f"{other_row.volunteer.user.first_name.lower()} {other_row.volunteer.user.last_name.lower()}"
                return OPEN_ROUTE.lower() < other_row_name


class SingleDayAssignment:
    """
    used to represent an assignment
    that is not every week on a particular day
    """

    def __init__(self, week_of_month, day_of_week):
        self.week_of_month = week_of_month
        self.day_of_week = day_of_week

    def __str__(self):
        if self.day_of_week is None and self.week_of_month is None:
            return "Bonus Pantry Route"
        else:
            return f"{abbreviated_weeks_of_month[self.week_of_month]} {abbreviated_days_of_week[self.day_of_week]}"


class MultipleDayAssignment:
    """
    used to represent an assignment that is
    every week on a particular day
    """

    def __init__(self, day_of_week):
        self.day_of_week = day_of_week

    def __str__(self):
        return f"{days_of_week[self.day_of_week]}s"


def generate_assignments_display(single_assignment_list):
    """
    :param single_assignment_list: list of SingleDayAssignment objects
    takes in a list of SingleDayAssignments and condenses
    down to MutipleDayAssignmentDisplays where possible, then returns
    comma joined list of MultipleDayAssignments and SingleDayAssignments as strings
    """
    # lists to store single day and multiple day assignments
    single_days = []
    multiple_days = []
    # hidden assignments list for indexing in the filter
    # this way a query for '1st Mon' will still match a row that says 'Mondays'
    hidden_days = []
    # loop over days of the week
    if single_assignment_list[0].day_of_week is None and single_assignment_list[0].week_of_month is None:
        return str(single_assignment_list[0])
    for i in range(1, 8):
        matching_assignments = list(
            filter(lambda item: item.day_of_week == i, single_assignment_list)
        )
        if len(matching_assignments) == 5:
            # assignment happens weekly
            multiple_days.append(MultipleDayAssignment(i))
            hidden_days += matching_assignments
        else:
            # can't condense
            single_days += matching_assignments

    # sort based on day of week
    multiple_days.sort(key=lambda item: item.day_of_week)
    # sort based on week and then day
    single_days.sort(key=lambda item: (item.week_of_month, item.day_of_week))

    # return visible assignments
    return ", ".join([str(item) for item in multiple_days] +
                     [str(item) for item in single_days])


@staff_member_required
def manage_assignments_table(request, job_pk=None, vol_pk=None):
    """
    generates the manage assignments table,
    this will get displayed in the manage_assignments template
    it is separated because it runs slowly
    job_pk will be 0 by when vol_pk is passed
    """
    row_dict = {}
    # get the appropriate assignments
    if job_pk is not None and job_pk != 0:
        query = Assignment.objects.filter(
            job=get_object_or_404(Job, pk=job_pk))
    elif vol_pk is not None and job_pk == 0:
        query = Assignment.objects.filter(
            volunteer=get_object_or_404(
                Volunteer, pk=vol_pk))
    else:
        query = Assignment.objects.all()

    for item in query:
        # create and edit the row items
        if (item.volunteer, item.job) in row_dict:
            row = row_dict[(item.volunteer, item.job)]
            row.hidden_assignments.append(
                SingleDayAssignment(item.week_of_month, item.day_of_week)
            )
        else:
            row_dict[(item.volunteer, item.job)] = Row(item)

    # create the visible and hidden assignments
    rows = row_dict.values()
    for row in rows:
        row.visible_assignments = generate_assignments_display(
            row.hidden_assignments)

    return render(
        request,
        "manage-assignments-table.html",
        {"rows": sorted(rows), "open_job": OPEN_ROUTE},
    )


@staff_member_required
def manage_assignments(request):
    """
    staff member view for manage_assignments
    """
    # url is for the async javascript function
    return render(request, "manage-assignments.html",
                  {"url": reverse("staff:manage_assignments_table")}, )


@staff_member_required
def edit_multiple_assignments(request, job_pk, vol_pk=None):
    """
    view to edit multiple assignments at once
    """
    job = get_object_or_404(Job, pk=job_pk)
    assigned_vol = get_object_or_404(
        Volunteer, pk=vol_pk) if vol_pk is not None else None
    assignments = Assignment.objects.filter(job=job, volunteer=assigned_vol)
    # if there are no assignments, return 404
    isBonusRoute = False
    if hasattr(job, 'route'):
        isBonusRoute = True if job.route.bonusRoute is not None else False

    if len(assignments) == 0:
        raise Http404
    form = EditMultipleAssignmentsForm(
        assignments, initial={
            "volunteer": assigned_vol}, isBonusRoute=isBonusRoute)
    if request.method == "POST":
        # check if it used the edit or delete button

        if "delete_assignments" in request.POST:
            # delete the checked assignments
            # checkboxes won't be in the request if they aren't checked
            if isBonusRoute:
                for assignment in assignments:
                    assignment.delete()
                return HttpResponseRedirect(reverse("staff:manage_assignments"))
            data = dict(request.POST)
            for key in data:
                # try to get the key
                day_of_month = days_of_month_tuples.get(key)
                # if it is not None, it is a valid day of month
                if day_of_month:
                    try:
                        asses_to_delete = assignments.filter(
                            day_of_week=day_of_month.day_of_week,
                            week_of_month=day_of_month.week_of_month,
                        )
                        for assignment in asses_to_delete:
                            assignment.delete()
                    except Assignment.DoesNotExist:
                        pass
            return HttpResponseRedirect(reverse("staff:manage_assignments"))

        else:
            # 'edit_assignments' in request.POST:
            form = EditMultipleAssignmentsForm(assignments, request.POST, isBonusRoute=isBonusRoute)
            if form.is_valid():
                return HttpResponseRedirect(
                    reverse("staff:manage_assignments"))

    # front end stuff for columns to appear nicely
    days = [(assignment.day_of_week, assignment.week_of_month)
            for assignment in assignments]
    # ensure they are sorted, this loop will only work on sorted days
    # need to sort them by day of week because columns are intended to be in
    # that order
    days.sort(key=lambda day: (day[1], day[0]))
    start_column_fields = []
    end_column_fields = []
    if isBonusRoute is False:
        for day in range(len(days)):
            # creating the columns
            if day == 0:
                # first item in first column
                start_column_fields.append(days_of_month_field_names[days[day]])
            if day != 0:
                if days[day][1] > days[day - 1][1]:
                    # it has switched to a new day of week
                    # so populate end and start
                    start_column_fields.append(
                        days_of_month_field_names[days[day]])
                    end_column_fields.append(
                        days_of_month_field_names[days[day - 1]])
            if day == len(days) - 1:
                # last item in list
                end_column_fields.append(days_of_month_field_names[days[day]])
    return render(
        request,
        "edit-multiple-assignments.html",
        {
            "form": form,
            "assigned_vol": assigned_vol,
            "job": job,
            "start_column_fields": start_column_fields,
            "end_column_fields": end_column_fields,
            "isBonusRoute": isBonusRoute
        },
    )
