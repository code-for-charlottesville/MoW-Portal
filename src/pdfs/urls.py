from django.urls import include, path, re_path

from . import views

app_name = "pdfs"

urlpatterns = [
    path("labels/<str:date>/", views.labels, name="generate_labels"),
    path("pet-labels/<str:date>/", views.pet_labels, name="generate_pet_labels"),
    path(
        "substitutions-report/<str:begin_date>/<str:end_date>/",
        views.substitutions_report,
        name="substitutions_report",
    ),
    path(
        "job-overview-report/<str:begin_date>/<str:end_date>/",
        views.job_overview_report,
        name="job_overview_report",
    ),
    path(
        "customer-status-report/<str:begin_date>/<str:end_date>/",
        views.customer_status_report,
        name="customer_status_report",
    ),
    path(
        "missing-feedback-report/<str:begin_date>/<str:end_date>/",
        views.missing_feedback_report,
        name="missing_feedback_report"
    ),
    path(
        "monthly-billing-report/<str:begin_date>/<str:end_date>/",
        views.monthly_billing_report,
        name="monthly_billing_report",
    ),
    path(
        "client-birthday-report/<int:month>/",
        views.client_birthday_report,
        name="client_birthday_report",
    ),
    path(
        "volunteer-birthday-report/<int:month>/",
        views.volunteer_birthday_report,
        name="volunteer_birthday_report",
    ),
    re_path(
        r"^daily-count-report/(?P<date>\d{2}-\d{2}-\d{4})/$",
        views.daily_count_report,
        name="daily_count_report",
    ),
    path(
        "volunteer-join-date-report",
        views.volunteer_join_date_report,
        name="volunteer_join_date_report",
    ),
    path(
        "generate-routes-report/<str:date>/",
        views.generate_routes_report,
        name="generate_routes_report",
    ),

    path(
        "get-all-customers-by-route",
        views.get_all_customers_by_route,
        name="get_all_customers_by_route"
    ),

    path(
        "bonus-pantry-report",
        views.generate_bonus_pantry_report,
        name="generate_bonus_pantry_report"
    ),
]
