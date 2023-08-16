import collections
import csv
import datetime
from logging import getLogger

import pdfkit

# Create your views here.
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import get_template
from pyvirtualdisplay import Display
from django.shortcuts import get_object_or_404


from interfaces.recurrence import date_to_day_of_month, months
from meals.constants import OPEN_ROUTE, OPEN_SUBSTITUTION, UNASSIGNED_JOB
from models.models import (
    Assignment,
    Customer,
    CustomerRecord,
    Run,
    Diet,
    Pet,
    PetFood,
    Route,
    Substitution,
    Volunteer,
)
from staff.views.job_management import actuals_to_display

_display = None

log = getLogger(__name__)

customer_feedback_fields = ["Date", "Route Number", "Client",
                            "Delivery Status", "Client Status", "Notes", "Volunteer"]


def to_pdf(html, styleSheetPath=None):
    global _display
    if not _display:
        _display = Display(visible=0, size=(320, 240)).start()
    options = {
        "page-size": "Letter",
        "margin-top": "0.74in",
        "margin-right": "0.39in",
        "margin-bottom": "0.39in",
        "margin-left": "0.39in",
        "print-media-type": True,
        "user-style-sheet": styleSheetPath
    }

    pdf = pdfkit.from_string(html, False, options)

    return HttpResponse(pdf, content_type="application/pdf")

#######helper functions#######


def reverse_date(date):
    return datetime.datetime.strptime(date, "%m-%d-%Y")


def get_run_row(obj, assignment_object):
    # find the volunteer associated with the route and date.
    if len(assignment_object) > 0:
        return [obj.run_date, obj.customer.route, obj.customer, obj.delivery_status, obj.customer_status, obj.notes, assignment_object[0].volunteer]
    else:
        return [obj.run_date, obj.customer.route, obj.customer, obj.delivery_status, obj.customer_status, obj.notes, "N/A"]


def initialize_feedback_report(begin_date, end_date, prefix=""):
    begin_date = reverse_date(begin_date)
    end_date = reverse_date(end_date)
    if begin_date == end_date:
        date = begin_date.strftime("%m-%d-%Y")
    else:
        date = begin_date.strftime("%m-%d-%Y") + \
            "--" + end_date.strftime("%m-%d-%Y")

    response = HttpResponse(content_type="text/csv")
    filename = prefix + "-" + date + ".csv"
    response["Content-Disposition"] = 'attachment; filename="' + filename + '"'

    writer = csv.writer(response)
    writer.writerow(customer_feedback_fields)

    feedback = Run.objects.filter(
        run_date__gte=begin_date, run_date__lte=end_date)

    return response, writer, feedback

#################################


@staff_member_required
def labels(request, date):
    date = datetime.datetime.strptime(date, "%m-%d-%Y")

    cust_query = Customer.objects.filter(
        active=1).exclude(
        route=None).order_by('route', 'last_name')
    cust_query = [c for c in cust_query if c.num_meals_on_day(date)]
    diet_query = Diet.objects.values()

    context = {
        "cust_query": cust_query,
        "diet_query": diet_query,
        "date": date}
    return render(request, "pdfs/label_pdf.html", context)


@staff_member_required
def pet_labels(request, date):
    date = datetime.datetime.strptime(date, "%m-%d-%Y")

    cust_query = Customer.objects.filter(
        active=1).exclude(
        route=None).order_by('route')
    cust_query = [
        c for c in cust_query if c.active and not c.date_range_excluded(date)]

    pet_query = Pet.objects.values()
    petfood_query = PetFood.objects.values()

    context = {'cust_query': cust_query,
               'pet_query': pet_query,
               'petfood_query': petfood_query,
               }

    # Front-end handles association of customers with pets/pet foods
    return render(request, "pdfs/label-pet-pdf.html", context)


class SubDisplay:
    def __init__(self, sub):
        self.job_name = sub.assignment.job.name
        self.route_number = sub.assignment.job.get_route_number()
        # job used for sorting
        self.job_name = sub.assignment.job.name
        self.job_type = sub.assignment.job.job_type.name
        if sub.volunteer:
            self.volunteer = f"{sub.volunteer.user.first_name} {sub.volunteer.user.last_name}"
        else:
            # it is open if there's not volunteer
            self.volunteer = "Open Substitution Request"
        if sub.assignment.volunteer:
            self.o_assignment = f"{sub.assignment.volunteer.user.first_name} {sub.assignment.volunteer.user.last_name}"
        else:
            # it is open if there's not volunteer
            self.o_assignment = OPEN_ROUTE


@staff_member_required
def substitutions_report(request, begin_date, end_date):
    """
    gets all of the information required for a substitution report
    takes in a beginning date and end date, displays for these days and
    everything in between
    """
    day_dict = {}  # passed into context
    begin_date_datetime = datetime.datetime.strptime(begin_date, "%m-%d-%Y")
    end_date_datetime = datetime.datetime.strptime(end_date, "%m-%d-%Y")
    count = (end_date_datetime - begin_date_datetime).days
    # loop over the count
    for i in range(count + 1):
        day = begin_date_datetime + datetime.timedelta(days=i)
        if day.isoweekday() == 6 or day.isoweekday() == 7:
            continue
        day_dict[day] = []
        # ge the subs table, loop over and create the person objects
        subs_on_day = Substitution.objects.filter(date=day)
        # loop over the substitutions for this day
        routes_on_day = []
        other_jobs_on_day = []
        for sub in subs_on_day:
            # create display item for context
            list_item = SubDisplay(sub)
            # append to routes or other jobs so items can be sorted
            if list_item.route_number != -1:
                routes_on_day.append(list_item)
            else:
                other_jobs_on_day.append(list_item)

        # sorting for display
        routes_on_day.sort(key=lambda r: (r.route_number, r.volunteer))
        # sort by type then by job name
        other_jobs_on_day.sort(key=lambda j: (j.job_type, j.job_name))
        day_dict[day] = routes_on_day + other_jobs_on_day

    template = get_template("pdfs/substitutions-report.html")
    return to_pdf(
        template.render(
            {
                "res": sorted(day_dict.items(), key=lambda item: (item[0])),
                "today": datetime.datetime.now(),
            }
        )
    )


@staff_member_required
def job_overview_report(request, begin_date, end_date):
    """
    generates the job overview report
    takes in a beginning date and end date, displays for these days and
    everything in between
    """
    begin_date_datetime = datetime.datetime.strptime(begin_date, "%m-%d-%Y")
    end_date_datetime = datetime.datetime.strptime(end_date, "%m-%d-%Y")
    dates = actuals_to_display(
        begin_date_datetime, end_date_datetime + datetime.timedelta(days=1)
    )
    template = get_template("pdfs/job-overview.html")
    return to_pdf(
        template.render(
            {
                "dates": dates,
                "open_substitution": OPEN_SUBSTITUTION,
                "unassigned_job": UNASSIGNED_JOB,
            }
        )
    )


@staff_member_required
def missing_feedback_report(request, begin_date, end_date):
    """
    generates the Customer Missing Feedback Status Report
    takes in a beginning date and end date, displays for these days and
    everything in between
    """
    response, writer, feedback = initialize_feedback_report(
        begin_date, end_date, "missing-feedback")

    if feedback is not None and len(feedback) > 0:
        for obj in feedback:
            # check if feedback exists. Add only those records that DO NOT have any feedback. /missingCustomerFeedback/ will insert blank records for incomplete/missing feedback
            if not obj.delivery_status and not obj.customer_status and obj.customer.route.id > -1:
                runDate = date_to_day_of_month(obj.run_date)

                # get assignments for volunteer users feedback
                try:
                    assignments = Assignment.objects.filter(
                        job=obj.customer.route, day_of_week=runDate.day_of_week, week_of_month=runDate.week_of_month)
                except Assignment.DoesNotExist:
                    assignments = None

                # get assignment id from assignments to find the substitute volunteer for the route
                if len(assignments) > 0:
                    for assignment in assignments:
                        assignmentId = assignment.id
                        subs = Substitution.objects.filter(
                            assignment=assignmentId, date=obj.run_date)

                # if assignment contains a sub, pass substitute object to
                # get_run_row function and print the correct volunteer name in the report
                if len(subs) > 0:
                    writer.writerow(get_run_row(obj, subs))
                else:
                    writer.writerow(get_run_row(obj, assignments))

    return response


@ staff_member_required
def customer_status_report(request, begin_date, end_date):
    """
    generates the Customer Status Report
    takes in a beginning date and end date, displays for these days and
    everything in between
    """
    response, writer, feedback = initialize_feedback_report(
        begin_date, end_date, "customer-statuses")

    if feedback is not None and len(feedback) > 0:
        for obj in feedback:
            if obj.delivery_status and obj.customer_status and obj.customer and obj.customer.route.id > -1:
                runDate = date_to_day_of_month(obj.run_date)

                # get assignments for volunteer users feedback
                try:
                    assignments = Assignment.objects.filter(
                        job=obj.customer.route, day_of_week=runDate.day_of_week, week_of_month=runDate.week_of_month)
                except Assignment.DoesNotExist:
                    assignments = None

                # get assignment id from assignments to find the substitute volunteer for the route
                if len(assignments) > 0:
                    for assignment in assignments:
                        assignmentId = assignment.id
                        subs = Substitution.objects.filter(
                            assignment=assignmentId, date=obj.run_date)

                # if assignment contains a sub, pass substitute object to
                # get_run_row function and print the correct volunteer name in the report
                if len(subs) > 0:
                    writer.writerow(get_run_row(obj, subs))
                else:
                    writer.writerow(get_run_row(obj, assignments))

    return response


@ staff_member_required
def monthly_billing_report(request, begin_date, end_date):

    # Parse some dates
    begin_date = datetime.datetime.strptime(begin_date, "%m-%d-%Y")
    end_date = datetime.datetime.strptime(end_date, "%m-%d-%Y")

    # Fetch all the CustomerRecord objects within the given range and sum up
    # the total meals per day
    date_meals_query = (
        CustomerRecord.objects.filter(
            num_meals__gte=1,
            date__gte=begin_date,
            date__lte=end_date) .values("date") .annotate(
            total_meals=Sum("num_meals")) .order_by("date"))

    # Convert the QuerySet to a usable dictionary
    date_meals = {}
    total = 0
    for record in date_meals_query:
        key = record["date"]
        value = record["total_meals"]

        date_meals[key] = value
        total += value

    # Fetch all the customers within query and count their number of meals
    customer_meals_query = (
        CustomerRecord.objects.filter(
            num_meals__gte=1,
            date__gte=begin_date,
            date__lte=end_date) .values(
            "customer",
            "payment_type",
            "route_assigned") .annotate(
                total_meals=Sum("num_meals")) .order_by("payment_type"))

    # Front-end logic handles separation and rendering of customer_meals
    # QuerySet

    # Last thing we need is ability to count meals by payment type
    payment_meals_query = (
        CustomerRecord.objects.filter(
            num_meals__gte=1,
            date__gte=begin_date,
            date__lte=end_date) .values("payment_type") .annotate(
            total_meals=Sum("num_meals"),
            num_customers=Count(
                "customer",
                distinct=True)) .order_by("payment_type"))

    # Convert to usable dictionary
    payments_meals = {}
    payments_customers = {}
    for elem in payment_meals_query:
        payment, meals, customers = (
            elem["payment_type"],
            elem["total_meals"],
            elem["num_customers"],
        )

        payments_meals[payment] = meals
        payments_customers[payment] = customers

    template = get_template("pdfs/monthly-billing.html")

    return to_pdf(
        template.render(
            {
                "date_meals": date_meals,
                "total": total,
                "cust_meals": customer_meals_query,
                "pay_meals": payments_meals,
                "pay_customers": payments_customers,
                "today": datetime.datetime.now(),
                "begin_date": begin_date,
                "end_date": end_date,
            }
        ), '/collected-static/pdfs/common.css'
    )


@ staff_member_required
def client_birthday_report(request, month):
    """
    generates a pdf list of client birthdays by inputted month
    """

    # get list of all the clients whose birthdays fall in the selected month
    birthdays = Customer.objects.filter(
        route__isnull=False,
        birth_date__month=str(month)).order_by(
        "birth_date__day",
        "birth_date__year",
        "route",
        "last_name",
        "first_name")
    template = get_template("pdfs/client-birthday-report.html")

    return to_pdf(
        template.render(
            {"birthdays": birthdays,
                "month": months[month], "today": datetime.datetime.now(), }
        )
    )


@ staff_member_required
def volunteer_birthday_report(request, month):
    """
    generates a pdf list of volunteer birthdays by inputted month
    """

    # get list of all the clients whose birthdays fall in the selected month
    birthdays = Volunteer.objects.filter(
        birth_date__month=str(month)).order_by(
        "birth_date__day", "birth_date__year", "user")
    template = get_template("pdfs/volunteer-birthday-report.html")

    return to_pdf(
        template.render(
            {"birthdays": birthdays,
                "month": months[month], "today": datetime.datetime.now(), }
        )
    )


@ staff_member_required
def volunteer_join_date_report(request):
    """
    generates a pdf list of volunteer join dates
    """

    # order clients by join date, then by name
    join_dates = Volunteer.objects.all().order_by("join_date", "user")
    template = get_template("pdfs/volunteer-join-date-report.html")

    return to_pdf(template.render(
        {"join_dates": join_dates, "today": datetime.datetime.now(), }))


@ staff_member_required
def daily_count_report(request, date):
    date_as_datetime = datetime.datetime.strptime(date, "%m-%d-%Y")
    diets = collections.defaultdict(int)
    total = 0
    frozen = 25
    no_diet = 0

    date = date_as_datetime

    # Count customer meals per diet
    for customer in Customer.objects.filter(active=True):
        total += customer.num_meals_on_day(date)
        if customer.diet is not None:
            diets[(customer.diet, customer.diet.code)
                  ] += customer.num_meals_on_day(date)
        else:
            no_diet += customer.num_meals_on_day(date)
            log.info(f"Customer {customer} has no diet.")

        # Customer wants frozen meals to just always be 25 for some reason.
        # if is_friday(date) and customer.num_weekend_meals and customer.num_meals_on_day(date):
        #     frozen += customer.num_weekend_meals
    total += frozen

    diet_list = []
    for key, val in diets.items():
        diet_list.append((key[0], key[1], val))
    context = {
        "diets": diet_list,
        "date": date,
        "day_of_week": date_as_datetime.strftime("%A"),
        "today": datetime.datetime.now(),
        "total": total,
        "frozen": frozen,
        "no_diet": no_diet,
    }

    template = get_template("pdfs/daily-count-report.html")

    return to_pdf(template.render(context))

@ staff_member_required
def get_all_customers_by_route(request):
    routes = Route.objects.all().order_by("number")
    routes = list(routes)

    # Context variable
    data = []
    today = datetime.datetime.now()

    for route in routes:
        # These are in correct route order
        custs = (
            Customer.objects.filter(
                active=1).exclude(
                route=None).filter(
                route__pk=route.pk)
                )
        total_customers = len(custs)
        # Append to data
        data.append(
            {"route": route, "customer_list": custs, "total_customers": total_customers, 
            "today": today}
        )

    template = get_template("pdfs/all-customers-by-route.html")
    context = {"data": data}

    return to_pdf(template.render(context), '/collected-static/pdfs/route_all_pdf.css')

@ staff_member_required
def generate_bonus_pantry_report(request):
    routes = Route.objects.all().order_by("number")
    routes = list(routes)

    # Context variable
    data = []
    today = datetime.datetime.now()

    for route in routes:
        # These are in correct route order
        custs = (
            Customer.objects.filter(
                active=1, receivesBonusPantryDelivery=True).exclude(
                route=None).filter(
                route__pk=route.pk)
                )
        total_customers = len(custs)
        # Append to data
        data.append(
            {"route": route, "customer_list": custs, "total_customers": total_customers, 
            "today": today}
        )

    template = get_template("pdfs/bonus-pantry-report.html")
    context = {"data": data}

    return to_pdf(template.render(context), '/collected-static/pdfs/route_all_pdf.css')


@ staff_member_required
def generate_routes_report(request, date):
    date = datetime.datetime.strptime(date, "%m-%d-%Y")
    date = datetime.date(year=date.year, month=date.month, day=date.day)
    # Just gonna loop over this query for each route_pk
    routes = Route.objects.all().order_by("number")
    routes = list(routes)

    # Context variable
    data = []

    for route in routes:
        # These are in correct route order
        custs = (
            Customer.objects.filter(
                active=1).exclude(
                route=None).filter(
                route__pk=route.pk))
        custs = [c for c in custs if c.num_meals_on_day(date)]

        actuals = Assignment.actuals(date, job=route)

        vols = ", ".join(str(act.volunteer) for act in actuals)

        # Count the meals the customer receives
        total_meals = 0
        for c in custs:
            total_meals += c.num_meals_on_day(date)

        # Append to data
        data.append({"route": route, "customer_list": custs,
                     "total_meals": total_meals, "date": date, "vols": vols})

    template = get_template("pdfs/generate-routes-report.html")
    context = {"data": data}

    return to_pdf(template.render(context), '/collected-static/pdfs/route_all_pdf.css')
