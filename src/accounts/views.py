import logging

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.shortcuts import HttpResponseRedirect, redirect, render
from django.template import RequestContext
from django.urls import reverse

from accounts.forms import LoginForm, SignUpForm, VolunteerForm
from meals.settings import EMAIL_HOST_USER
from models.models import Volunteer
from staff.views import index as staff_index
from volunteers.views import index as vol_index

log = logging.getLogger(__name__)


# Create your views here.


def home(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            log.info(f"{request.user.username} recognized as staff.")
            return HttpResponseRedirect(reverse("staff:index"))
        log.info(f"{request.user.username} recognized as volunteer.")
        return HttpResponseRedirect(reverse("volunteers:index"))
    return render(request, "home.html", {})


# login/logout don't need developer-created views, those are provided by
# the Django auth module
def login_user(request):
    form = LoginForm(request.POST or None)
    if request.POST and form.is_valid():
        user = form.login(request)
        if user:
            auth_login(request, user)
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            else:
                return redirect("home")  # Redirect to a success page.
    return render(request,
                  "../templates/registration/login.html",
                  {"form": form})


# Privacy Policy
def privacy_policy(request):
    return render(request,
                  "../templates/privacy_policy.html",
                  {})
