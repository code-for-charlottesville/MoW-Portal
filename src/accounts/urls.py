from django.contrib import admin
from django.urls import include, path  # new

from . import views

urlpatterns = [
    path("login/", views.login_user, name="login_user"),
]
