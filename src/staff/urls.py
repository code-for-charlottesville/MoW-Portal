# from staff.views import create_customer, RecurrenceListView, edit_assignment, index
from django.apps import apps
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import include, path, re_path, reverse_lazy
from django.views.generic import ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

import staff.all_views as views
from staff.forms import CustomerDateRangeForm

app_name = "staff"

urlpatterns = [
    path("", views.index, name="index"),
    path("create-customer/", views.create_customer, name="create_customer"),
    path(
        "manage-substitutions/",
        views.manage_substitutions,
        name="manage_substitutions"),
    path(
        "manage-assignments/",
        views.manage_assignments,
        name="manage_assignments"),
    path(
        "manage-assignments-table/",
        views.manage_assignments_table,
        name="manage_assignments_table",
    ),
    path(
        "manage-assignments-table/<int:job_pk>/",
        views.manage_assignments_table,
        name="manage_assignments_table",
    ),
    # This table will populate using job_pk if job_pk is not 0
    path(
        "manage-assignments-table/<int:job_pk>/<int:vol_pk>/",
        views.manage_assignments_table,
        name="manage_assignments_table",
    ),
    path(
        "edit-multiple-assignments/<int:job_pk>/<int:vol_pk>/",
        views.edit_multiple_assignments,
        name="edit_multiple_assignments",
    ),
    path(
        "edit-multiple-assignments/<int:job_pk>/",
        views.edit_multiple_assignments,
        name="edit_multiple_assignments",
    ),
    path(
        "recurrences/create/",
        views.create_recurrence,
        name="create_recurrence"),
    path(
        "create-substitution/",
        views.create_substitution,
        name="create_substitution"),
    path(
        "async-parse-assignment/<str:date>/<int:job_pk>/",
        views.async_parse_assignment,
        name="async_parse_assignment",
    ),
    path(
        "edit-substitution/<int:pk>/",
        views.edit_substitution,
        name="edit_substitution"),
    path(
        "delete-substitution/<int:pk>/", views.delete_substitution, name="delete_substitution",
    ),
    path(
        "remove-substitute/<int:pk>/",
        views.remove_substitute,
        name="remove_substitute"),
    path("spawn-open-jobs/", views.spawn_open_jobs, name="spawn_open_jobs"),
    path("manage-jobs/", views.manage_jobs, name="manage_jobs"),
    path("manage-jobs/<str:date>/", views.manage_jobs, name="manage_jobs",),
    path("manage-customers/", views.manage_customers, name="manage_customers"),
    path("edit-customer/<int:pk>/", views.edit_customer, name="edit_customer"),
    path(
        "manage-volunteers/",
        views.manage_volunteers,
        name="manage_volunteers"),
    path(
        "edit-volunteer/<int:pk>/",
        views.edit_volunteer,
        name="edit_volunteer"),
    path(
        "delete-volunteer/<int:pk>/",
        views.delete_volunteer,
        name="delete_volunteer"),
    path(
        "delete-customer/<int:pk>/",
        views.delete_customer,
        name="delete_customer"),
    path(
        "create-announcement/",
        views.create_announcement,
        name="create_announcement"),
    path(
        "manage-open-job/<int:assignment_pk>/<str:date>/",
        views.manage_open_job,
        name="manage_open_job",
    ),
    path(
        "delete-announcement/<int:pk>/", views.delete_announcement, name="delete_announcement",
    ),
    path("create-job/", views.create_job, name="create_job"),
    path("edit-job/<int:pk>/", views.edit_job, name="edit_job"),
    path("delete-job/<int:pk>/", views.delete_job, name="delete_job"),
    path("parse-date-form", views.parse_date_form, name="parse_date_form"),
    path(
        "date-range-form/<str:report_type>/",
        views.date_range_form,
        name="date_range_form",
    ),
    path("month-form/<str:report_type>/", views.month_form, name="month_form",),
    path(
        "single-date-form/<slug:report_type>/",
        views.single_date_form,
        name="single_date_form",
    ),
    path("create-volunteer/", views.create_volunteer, name="create_volunteer"),
    path(
        "volunteer-join-date-report",
        views.volunteer_join_date_report,
        name="volunteer_join_date_report",
    ),
    path(
        "delete-payment/<int:pk>/",
        views.delete_payment,
        name="delete_payment"),
    path("delete-pet/<int:pk>/", views.delete_pet, name="delete_pet"),
    path("delete-diet/<int:pk>/", views.delete_diet, name="delete_diet"),
    path(
        "delete-petfood/<int:pk>/",
        views.delete_petfood,
        name="delete_petfood"),
    path(
        "delete-daterange/<int:pk>/",
        views.delete_daterange,
        name="delete_daterange"),
    path("email/", views.send_email, name="email"),
    path(
        "export-customers",
        views.export_customers,
        name="export_customers"
    ),
    path(
        "export-volunteers",
        views.export_volunteers,
        name="export_volunteers"
    ),
    re_path(
        r"^volunteer-autocomplete/$",
        staff_member_required(views.VolunteerAutocomplete.as_view()),
        name="volunteer-autocomplete",
    ),
    re_path(
        r"^assignment-autocomplete/$",
        staff_member_required(views.AssignmentAutocomplete.as_view()),
        name="assignment-autocomplete",
    ),
    re_path(
        r"^customer-autocomplete/$",
        staff_member_required(views.CustomerAutocomplete.as_view()),
        name="customer-autocomplete",
    ),
]



wanted_models = ["pet", "payment", "diet", "petfood",
                 "daterange"]  # maybe add daterange here?
for model in apps.get_app_config("models").get_models():
    mname = model._meta.model_name
    if mname not in wanted_models:
        continue
    else:
        if mname == "daterange":
            kwargs = {"form_class": CustomerDateRangeForm}
        else:
            kwargs = {"fields": "__all__"}
        create_route = path(
            "create-{}".format(mname),
            staff_member_required(
                CreateView.as_view(
                    model=model,
                    template_name="create-{}.html".format(mname),
                    success_url=reverse_lazy("staff:manage_{}s".format(mname)),
                    **kwargs,
                )
            ),
            name="create_{}".format(mname),
        )
        edit_route = path(
            "edit-{}/<int:pk>/".format(mname),
            staff_member_required(
                UpdateView.as_view(
                    model=model,
                    template_name="edit-{}.html".format(mname),
                    success_url=reverse_lazy("staff:manage_{}s".format(mname)),
                    **kwargs,
                )
            ),
            name="edit_{}".format(mname),
        )
        manage_route = path(
            "manage-{}s".format(mname),
            staff_member_required(
                ListView.as_view(
                    model=model,
                    template_name="manage-{}s.html".format(mname),
                )
            ),
            name="manage_{}s".format(mname),
        )
        urlpatterns.append(create_route)
        urlpatterns.append(edit_route)
        urlpatterns.append(manage_route)
