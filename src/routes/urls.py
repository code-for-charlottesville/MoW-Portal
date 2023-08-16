from django.urls import include, path

from . import views

app_name = "routes"

urlpatterns = [
    path("<int:route_number>/", views.view_route, name="view_route"),
    path("<int:route_number>/<str:date>/", views.view_route_day, name="view_route_day"),
    path(
        "move-customer/<int:route_number>/<int:index>/<str:direction>/",
        views.move_customer,
        name="move_customer",
    ),
    path(
        "remove-customer/<int:route_number>/<int:customer_pk>/",
        views.remove_customer_from_route,
        name="remove_customer_from_route",
    ),
    path(
        "add-and-remove-customer/<int:customer_pk>/<int:destination_route_number>/",
        views.add_and_remove_customer_from_route,
        name="add_and_remove_customer_from_route",
    ),
    path("parse-date-form/<int:route_number>/", views.parse_date_form, name="parse_date_form"),
]
