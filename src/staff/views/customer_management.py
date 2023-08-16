"""
Views file for customer management
"""

from logging import getLogger

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render, reverse

from models.models import Customer, Run, Assignment
from staff.forms import AddressForm, CustomerForm, CustomerRecurrenceForm

import csv
import datetime

log = getLogger(__name__)


@staff_member_required
def create_customer(request):
    """
    create customer page
    """
    if request.method == "POST":

        form = CustomerForm(request.POST)
        rec_form = CustomerRecurrenceForm(request.POST)
        addr_form = AddressForm(request.POST)
        if form.is_valid() and rec_form.is_valid() and addr_form.is_valid():
            form.meal_recurrence = rec_form.cleaned_data["meal_recurrence"]
            form.save(commit=False)
            rec_form.save(commit=False)
            address = addr_form.cleaned_data["address"]
            lat = request.POST.get("address_latitude", None)
            lon = request.POST.get("address_longitude", None)
            address.save()
            Customer.objects.create(
                address=address,
                **form.cleaned_data,
                lat=lat,
                lon=lon)

            return redirect("home")
        else:
            context = {
                "form": form,
                "rec_form": rec_form,
                "addr_form": addr_form,
            }
            return render(
                request,
                "create-customer.html",
                context)  # this will show errors

    form = CustomerForm()
    rec_form = CustomerRecurrenceForm()
    addr_form = AddressForm()
    context = {
        "form": form,
        "rec_form": rec_form,
        "addr_form": addr_form,
    }
    return render(request, "create-customer.html", context)


@staff_member_required
def manage_customers(request):
    """
    view for managing customers
    will bring up all custome
    """
    # get all the substitutions in the DB from today on
    all_customers = Customer.objects.all().order_by("first_name", "last_name")
    return render(request, "manage-customers.html", {"cstmrs": all_customers})


@staff_member_required
def edit_customer(request, pk):
    """
    edit customer page
    """

    instance = get_object_or_404(Customer, pk=pk)
    form = CustomerForm(instance=instance)
    rec_form = CustomerRecurrenceForm(instance=instance)
    addr_form = AddressForm(initial={"address": instance.address})
    customer_route = instance.route  # needed for buton in template
    customer_address = instance.address
    if request.method == "POST":
        form = CustomerForm(request.POST, instance=instance)
        rec_form = CustomerForm(request.POST, instance=instance)
        addr_form = AddressForm(request.POST)
        if form.is_valid() and rec_form.is_valid() and addr_form.is_valid():

            form.save()
            rec_form.save()
            lat = request.POST.get("address_latitude", None)
            lon = request.POST.get("address_longitude", None)
            addr = addr_form.cleaned_data["address"]
            addr.save()
            instance.lon = lon
            instance.lat = lat
            instance.address = addr
            instance.save()

            return HttpResponseRedirect(reverse("staff:manage_customers"))
        else:
            context = {
                "form": form,
                "rec_form": rec_form,
                "addr_form": addr_form,
                "customer_route": customer_route,
            }
            return render(
                request,
                "edit-customer.html",
                context)  # this will show errors
    context = {
        "form": form,
        "rec_form": rec_form,
        "customer_route": customer_route,
        "addr_form": addr_form,
    }
    return render(request, "edit-customer.html", context)


@staff_member_required
def delete_customer(request, pk):
    """
    :param pk: primary key of customer object
    delete the row corresponding to the primary key,
    404 if the item isn't found
    redirect back to manage-custome
    """
    customer_req = get_object_or_404(Customer, pk=pk)
    customer_req.delete()
    return HttpResponseRedirect(reverse("staff:manage_customers"))


@staff_member_required
def export_customers(request):
    # Create the HttpResponse object with the appropriate CSV header
    response = HttpResponse(content_type="text/csv")
    today = str(datetime.datetime.now())
    filename = "customer-export-" + today + ".csv"
    response["Content-Disposition"] = 'attachment; filename="' + filename + '"'

    blank_customer = Customer()
    field_names = [field.name for field in blank_customer._meta.fields]

    writer = csv.writer(response)
    writer.writerow(field_names)

    customers = Customer.objects.filter(active=1)

    for obj in customers:
        writer.writerow([getattr(obj, field) for field in field_names])

    return response


