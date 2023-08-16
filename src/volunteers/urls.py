from django.contrib import admin
from django.urls import include, path  # new

from . import views

app_name = "volunteers"

urlpatterns = [
    path(
        "",
        views.index,
        name="index"),
    path(
        "my_jobs/",
        views.my_jobs,
        name="my_jobs"),
    path(
        "request_substitute/",
        views.request_substitute,
        name="request_substitute"),
    path(
        "open_jobs/",
        views.open_jobs,
        name="open_jobs"),
    path(
        "take_substitution/",
        views.take_substitution,
        name="take_substitution"),
    path(
        "view_profile/",
        views.view_profile,
        name="view_profile"),
]
