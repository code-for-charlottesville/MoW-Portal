from dateutil.relativedelta import relativedelta
from logging import getLogger
import datetime
import requests
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render, reverse

import config.config as CONFIG
from meals.constants import MOW_LAT, MOW_LON
from models.models import Customer, Job, Route, Volunteer
from routes import utility
from routes.forms import AddCustomerForm, RouteFormNoType
from staff.forms import DateForm
from staff.views.job_management import get_emails_by_job

log = getLogger(__name__)


def get_customers(route, date=None, isBonusRoute=False):
    """
    :param route: route instance
    :param date: datetime or None
    get the customers in the correct order on the route
    if date is passed, filter out the ones that don't receive meals
    query google maps api to add data to the objects then return the list
    """
    # get_customer_order returns a list of pks, we need customer objects
    if isBonusRoute and date:
        recurrenceDate = route.recurrence.after(date, inc=True, dtstart= date)
        if recurrenceDate == date:
            return Customer.objects.filter(route=route.bonusRoute, receivesBonusPantryDelivery=True).order_by("_order")
        else:
            return []
    elif isBonusRoute:
        customers = Customer.objects.filter(route=route, receivesBonusPantryDelivery=True).order_by("_order")
    else:
        customers = Customer.objects.filter(route=route).order_by("_order")

    if date is not None:
        customers = [c for c in customers if c.num_meals_on_day(date)]
    return customers


# Create your views here.
@staff_member_required
def view_route(request, route_number):
    """
    Route detail page
    """
    route_instance = get_object_or_404(Route, number=route_number)
    isBonusRoute = False if route_instance.bonusRoute is None else True
    routeId = route_instance.bonusRoute if isBonusRoute else route_instance
    route_name = route_instance.name
    route_form = RouteFormNoType(instance=route_instance, initial= { 'bonusRoute': routeId})
    is_family_friendly_route = route_instance.family_friendly_route
    job_pk = Job.objects.get(name=route_instance.name).pk
    # https://docs.djangoproject.com/en/3.0/ref/forms/fields/#django.forms.ModelChoiceField
    add_customer_form = AddCustomerForm(initial={"route": route_instance})

    add_customer_form.fields["customer"].queryset = Customer.objects.exclude(route=route_instance)
    # keeping this up here so we don't lose speed querying for customers
    if request.method == "POST":
        # if the customer_form is submitted, this will be in the request
        if "add_customer_form" in request.POST:
            add_customer_form = AddCustomerForm(request.POST)
            # validate and save the changes
            if add_customer_form.is_valid():
                # customer is added in the is_valid call
                return HttpResponseRedirect(
                    reverse(
                        "routes:view_route",
                        args=[route_number]))

        else:
            # we will just validate against the route_form
            route_form = RouteFormNoType(request.POST, instance=route_instance)
            # validate and save the changes
            if route_form.is_valid():
                route_form.save()
                route_number = route_form.cleaned_data.get("number")
                return HttpResponseRedirect(
                    reverse(
                        "routes:view_route",
                        args=[route_number]))

    return render(
        request,
        "route-detail.html",
        {
            "customers": get_customers(routeId, isBonusRoute=isBonusRoute),
            "mainRoute": False if route_instance.bonusRoute is None else route_instance.bonusRoute.name,
            "route_num": route_number,
            "jobPk": job_pk, 
            "route_form": route_form,
            "route_name": route_name,
            "add_customer_form": add_customer_form,
            "emails": get_emails_by_job(route_instance),
            "url": reverse("staff:manage_assignments_table", args=[job_pk]),
            "date_picker_date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "MOW_LAT": MOW_LAT,
            "MOW_LON": MOW_LON,
            "API_KEY": CONFIG.BROWSER_GOOGLE_API_KEY,
            "isBonusRoute": isBonusRoute,
            "is_family_friendly_route": is_family_friendly_route,
        },
    )


@login_required
def view_route_day(request, route_number, date):
    """
    view route on a specific date
    """
    # get the route instance
    route = get_object_or_404(Route, number=route_number)
    isBonusRoute = False if route.bonusRoute is None else True
    is_staff = request.user.is_staff
    # convert the url to a datetime, if exception redirect based on auth
    try:
        date = datetime.datetime.strptime(date, "%m-%d-%Y")
    except ValueError:
        if is_staff:
            # go the the no specific day view if staff
            return HttpResponseRedirect(
                reverse(
                    "routes:view_route", args=[
                        route.number]))
        else:
            # just 404 for the volunteers
            raise Http404

    navbar = "navbar_staff.html" if is_staff else "navbar_volunteer.html"

    return render(
        request,
        "route-on-day.html",
        {
            "customers": get_customers(route, date, isBonusRoute),
            "route_name": route.name,
            "route_num": route_number,
            "date_picker_date": date.strftime("%Y-%m-%d"),
            "date_display": date.strftime("%A, %B %d, %Y"),
            "navbar": navbar,
            "is_staff": is_staff,
            "MOW_LAT": MOW_LAT,
            "MOW_LON": MOW_LON,
            "API_KEY": CONFIG.BROWSER_GOOGLE_API_KEY,
        },
    )


@staff_member_required
def move_customer(request, route_number, index, direction):

    # get route or 404
    route = get_object_or_404(Route, number=route_number)

    # initiate swap
    customers = list(route.get_customer_order())
    list_length = len(customers)

    # validate swap can happen and perform it
    if index >= 0 and index <= list_length - 1:
        other_index = index
        if direction == "down" and index < list_length - 1:
            # swap
            other_index = index + 1
        elif direction == "up" and index > 0:
            # swap
            other_index = index - 1
        else:
            # not a valid direction
            pass

        customers[index], customers[other_index] = (
            customers[other_index],
            customers[index],
        )
        route.set_customer_order(customers)

    return HttpResponseRedirect(
        reverse(
            "routes:view_route",
            args=[route_number]))


@staff_member_required
def remove_customer_from_route(request, route_number, customer_pk):
    """
    :param route_number: route number
    :param customer_pk: customer primary key
    calls utility function to remove customer from the route
    then redirects back to route. Exposed url
    """
    # will need the customer
    customer = get_object_or_404(Customer, pk=customer_pk)
    # if the customer is on the route, remove and adjust order
    utility.remove_customer_from_route(customer)
    # redirect back to the route in all cases
    return HttpResponseRedirect(
        reverse(
            "routes:view_route",
            args=[route_number]))


@staff_member_required
def add_and_remove_customer_from_route(
        request, customer_pk, destination_route_number):
    """
    :param route_pk: route primary key
    :param customer_pk: customer primary key
    calls utility function to remove customer
    """
    # get the objects, return 404 if they don't exist
    customer = get_object_or_404(Customer, pk=customer_pk)
    route = get_object_or_404(Route, number=destination_route_number)

    # remove the customer
    utility.remove_customer_from_route(customer)

    # add the customer to the destination route
    utility.add_customer_to_route(customer, route)

    return HttpResponseRedirect(
        reverse(
            "routes:view_route",
            args=[destination_route_number]))


@staff_member_required
def parse_date_form(request, route_number):
    """
    This handles the form on the view_route page
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

    return HttpResponseRedirect(
        reverse("routes:view_route_day", args=[route_number, date_str])
    )
