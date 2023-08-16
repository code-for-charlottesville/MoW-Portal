"""
Views file for managing volunteers
"""

from logging import getLogger

from django import forms
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.db.models import Max

from accounts.forms import SignUpForm, VolunteerForm
from models.models import Assignment, Volunteer, Substitution, VolunteerRecord
from staff.forms import VolunteerUserForm, AddressForm
from staff.views.email import send_email, reset_password

import csv
import datetime
import time

log = getLogger(__name__)

# Signup is not an option available in auth so we have to create our own
# view/url for it


@staff_member_required
def create_volunteer(request):
    if request.method == "POST":
        user_form = SignUpForm(request.POST)
        vol_form = VolunteerForm(request.POST)
        addr_form = AddressForm(request.POST)
        if user_form.is_valid() and vol_form.is_valid() and addr_form.is_valid():
            address = addr_form.cleaned_data["address"]
            address.save()

            username = user_form.cleaned_data.get("username")
            email = user_form.cleaned_data.get("email")
            raw_password = User.objects.make_random_password()

            # manually set up user with a random password
            user_form.password1 = raw_password
            user_form.password2 = raw_password
            user_form.save()
            user = User.objects.get(username=username)

            # volunteer is automatically created on user create, get that
            # volunteer
            vol = Volunteer.objects.get(user=user)
            vol.address = address
            vol.save()
            other_vol_form = VolunteerForm(request.POST, instance=vol)
            other_vol_form.save()

            # send password reset email
            reset_password(email, request)

            return HttpResponseRedirect(reverse("staff:manage_volunteers"))

    else:
        user_form = SignUpForm()
        vol_form = VolunteerForm()
        addr_form = AddressForm()
    context = {
        "user_form": user_form,
        "vol_form": vol_form,
        "addr_form": addr_form}
    return render(request, "create-volunteer.html", context)


@staff_member_required
def manage_volunteers(request):
    """
    view for managing volunteers
    will bring up all volunteers
    """

    all_volunteers = Volunteer.objects.annotate(Max("record__date")).order_by(
        "user__first_name", "user__last_name"
    )
    return render(request, "manage-volunteers.html", {"vols": all_volunteers})

def nth_day_of_month(assignment, month=None):
    try:
        day_of_week = assignment.day_of_week - 1
        week_of_month = assignment.week_of_month
        first_possible_day = {1: 1, 2: 8, 3: 15, 4: 22, 5: 29}[week_of_month]
        if month == None:
            d = datetime.datetime.now().replace(day=first_possible_day)
        else:
            d = datetime.datetime.now().replace(day=first_possible_day, month=month)
        w = d.weekday()
        if w != day_of_week:
            d = d.replace(day=(first_possible_day + (day_of_week - w) % 7))
        return d.day
    except ValueError:
        return -1

@staff_member_required
def edit_volunteer(request, pk):
    """
    edit volunteer page
    """

    instance = get_object_or_404(Volunteer, pk=pk)
    form = VolunteerForm(instance=instance)
    user_form = VolunteerUserForm(instance=instance.user)
    addr_form = AddressForm(initial={"address": instance.address})

    if request.method == "POST":
        form = VolunteerForm(request.POST, instance=instance)
        user_form = VolunteerUserForm(request.POST, instance=instance.user)
        addr_form = AddressForm(request.POST)
        if form.is_valid() and user_form.is_valid() and addr_form.is_valid():
            form.save(commit=False)
            user_form.save(commit=False)
            # make sure unique usernames are maintained
            cleaned_username = user_form.cleaned_data["username"].lower()

            user_form.username = cleaned_username.lower()
            addr = addr_form.cleaned_data["address"]
            addr.save()
            instance.address = addr
            instance.save()
            form.save()
            user_form.save()

            return HttpResponseRedirect(reverse("staff:manage_volunteers"))

        else:
            context = {
                "form": form,
                "user_form": user_form,
                "addr_form": addr_form}
            return render(
                request,
                "edit-volunteer.html",
                context)  # this will show errors

    context = {
        "form": form,
        "user_form": user_form,
        "url": reverse(
            "staff:manage_assignments_table",
            args=[
                0,
                instance.pk]),
        "addr_form": addr_form,
    }
    return render(request, "edit-volunteer.html", context)


@staff_member_required
def delete_volunteer(request, pk):
    """
    :param pk: primary key of volunteer object
    delete the row corresponding to the primary key,
    404 if the item isn't found
    redirect back to manage-volunteer
    """
    volunteer_req = get_object_or_404(Volunteer, pk=pk)
    assignments = Assignment.objects.filter(volunteer=volunteer_req)

    for assignment in assignments:
        assignment.volunteer = None
        assignment.save()
    volunteer_req.delete()
    return HttpResponseRedirect(reverse("staff:manage_volunteers"))


@staff_member_required
def export_volunteers(request):
    # Create the HttpResponse object with the appropriate CSV header
    response = HttpResponse(content_type="text/csv")
    today = str(datetime.datetime.now())
    filename = "volunteer-export-" + today + ".csv"
    response["Content-Disposition"] = 'attachment; filename="' + filename + '"'

    blank_volunteer = Volunteer()
    field_names = [field.name for field in blank_volunteer._meta.fields]

    writer = csv.writer(response)
    writer.writerow(field_names)

    volunteers = Volunteer.objects.all()

    for obj in volunteers:
        writer.writerow([getattr(obj, field) for field in field_names])

    return response
