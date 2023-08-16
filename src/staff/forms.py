import datetime

from address.forms import AddressField
from dal import autocomplete
from django import forms
from django.contrib.auth import get_user_model
from django.forms import ModelForm

from interfaces.recurrence import (
    date_to_day_of_month,
    days_of_month_field_names,
    days_of_month_titles,
    days_of_month_tuples,
    days_of_week,
    months,
    weeks_of_month,
)
from models.models import (
    Assignment,
    Customer,
    DateRange,
    Job,
    JobType,
    ManagerAnnouncement,
    Route,
    Substitution,
    User,
    Volunteer,
)


def get_job_choices():
    """
    creating the choices for "job" fields
    client requested they be rendered in a particular order
    with routes displaying first
    """
    jobs = Job.objects.all()
    routes = []
    other_jobs = []
    for job in jobs:
        job.route_number = job.get_route_number()
        if job.route_number == -1:
            # not a route
            other_jobs.append(job)
        else:
            routes.append(job)

    # sort the jobs
    routes.sort(key=lambda route: route.route_number)
    other_jobs.sort(
        key=lambda other_job: (
            other_job.job_type.name,
            other_job.name))
    jobs = routes + other_jobs
    # create the choices
    # iterable of tuples, first value goes in the value attribute, second is
    # the innerHTML
    return [(None, "Please select a job.")] + \
        [(job.pk, job.name) for job in jobs]


# https://docs.djangoproject.com/en/2.2/topics/forms/modelforms/


class DateInput(forms.DateInput):
    input_type = "date"

class JobTypeForm(forms.Form):
    jobType = forms.ModelChoiceField(queryset=JobType.objects.all())
    class Meta:
        model = JobType
        fields = ['name']
        labels = { 'jobType': "Job Type"}




class JobForm(ModelForm):
    """
    for validation of job in create job
    """

    class Meta:
        model = Job
        fields = ["name", "num_vols_required", "job_type"]
        labels = {"num_vols_required": "Number of volunteers required"}
        error_messages = {
            'job_type': {'Required': "Job Type is required", }}

    def __init__(self, *args, **kwargs):
        super(JobForm, self).__init__(*args, **kwargs)
        # sets the prefix for all html ids in the form
        self.auto_id = 'job_%s'


class JobFormNoType(ModelForm):
    """
    for validation of job in edit job
    """

    class Meta:
        model = Job
        fields = ["name", "num_vols_required", "recurrence"]
        labels = {"num_vols_required": "Number of volunteers required"}


class RouteForm(ModelForm):
    """
    For validation of routes in create job
    """

    class Meta:
        model = Route
        fields = [
            "name",
            "num_vols_required",
            "number",
            "description",
            "job_type",
        ]
        labels = {"num_vols_required": "Number of volunteers required"}
        error_messages = {
            "name": {"required": "name is required", },
            "number": {"required": "route number is required", },
            "num_vols_required": {"required": "Number of volunteers is required", }, }

    def __init__(self, *args, **kwargs):
        super(RouteForm, self).__init__(*args, **kwargs)
        # sets the prefix for all html ids in the form
        self.auto_id = 'route_%s'

class BonusDeliveryForm(ModelForm):

    bonusRoute = forms.ModelChoiceField(queryset=Route.objects.none())

    class Meta:
        model = Route
        fields = [
            "name",
            "num_vols_required",
            "recurrence",
            "number",
            "description",
            "job_type",
            "bonusRoute"
        ]
        labels = {"num_vols_required": "Number of volunteers required"}
        error_messages = {
            "name": {"required": "name is required", },
            "bonusRoute": {"required": "bonus route is required", },
            "number": {"required": "route number is required", },
            "num_vols_required": {"required": "Number of volunteers is required", },
            "recurrence": {"recurrence_required": "Job recurrence cannot be blank, please add recurrence data", },
        }
    def __init__(self, *args, **kwargs):
        super(BonusDeliveryForm, self).__init__(*args, **kwargs)
        # sets the prefix for all html ids in the form
        self.auto_id = 'bonus_route_%s'
        self.fields['bonusRoute'].queryset = Route.objects.filter(route__bonusRoute=None).filter(bonusRoute=None)

class RouteFormNoType(ModelForm):
    """
    for validation of route in edit job
    """

    class Meta:
        model = Route
        fields = [
            "name",
            "num_vols_required",
            "recurrence",
            "number",
            "description",
            "bonusRoute",
            "family_friendly_route"
        ]
        labels = {"num_vols_required": "Number of volunteers required"}
        error_messages = {
            "name": { "required": "name is required", },
            "number": { "required": "route number is required", },
            "num_vols_required": { "required": "num vols required is required", },
            "bonusRoute": {"required": "bonus route is required", }, }


class CustomerForm(ModelForm):
    class Meta:
        model = Customer
        fields = [
            "historical_route",
            "join_date",
            "pays",
            "active",
            "first_name",
            "last_name",
            "phone",
            "printed_notes",
            "birth_date",
            "sex",
            "contact",
            "contact_phone",
            "diet",
            "cold_diet_restrictions",
            "hot_diet_restrictions",
            "pet",
            "petfood",
            "end_date",
            "end_reason",
            "referred",
            "ref_phone",
            "bill_to",
            "notes",
            "meal_recurrence",
            "num_weekend_meals",
            "receivesBonusPantryDelivery"
        ]
        widgets = {
            "birth_date": DateInput(format=("%Y-%m-%d")),
            "join_date": DateInput(format=("%Y-%m-%d")),
        }


class CustomerRecurrenceForm(ModelForm):
    class Meta:
        model = Customer
        fields = ["meal_recurrence"]


class AddressForm(forms.Form):
    address = AddressField()


class CreateAssignmentForm(forms.Form):
    volunteer = forms.ModelChoiceField(
        queryset=Volunteer.objects.all(),
        widget=autocomplete.ModelSelect2(url="/staff/volunteer-autocomplete"),
        required=False,
    )
    job = forms.ChoiceField(
        error_messages={
            "invalid_choice": "Please select a job.",
            "required": "Please select a job.",
        },
        required=True,
    )

    first_monday = forms.BooleanField(required=False, label="First Monday")
    first_tuesday = forms.BooleanField(required=False, label="First Tuesday")
    first_wednesday = forms.BooleanField(
        required=False, label="First Wednesday")
    first_thursday = forms.BooleanField(required=False, label="First Thursday")
    first_friday = forms.BooleanField(required=False, label="First Friday")
    second_monday = forms.BooleanField(required=False, label="Second Monday")
    second_tuesday = forms.BooleanField(required=False, label="Second Tuesday")
    second_wednesday = forms.BooleanField(
        required=False, label="Second Wednesday")
    second_thursday = forms.BooleanField(
        required=False, label="Second Thursday")
    second_friday = forms.BooleanField(required=False, label="Second Friday")
    third_monday = forms.BooleanField(required=False, label="Third Monday")
    third_tuesday = forms.BooleanField(required=False, label="Third Tuesday")
    third_wednesday = forms.BooleanField(
        required=False, label="Third Wednesday")
    third_thursday = forms.BooleanField(required=False, label="Third Thursday")
    third_friday = forms.BooleanField(required=False, label="Third Friday")
    fourth_monday = forms.BooleanField(required=False, label="Fourth Monday")
    fourth_tuesday = forms.BooleanField(required=False, label="Fourth Tuesday")
    fourth_wednesday = forms.BooleanField(
        required=False, label="Fourth Wednesday")
    fourth_thursday = forms.BooleanField(
        required=False, label="Fourth Thursday")
    fourth_friday = forms.BooleanField(required=False, label="Fourth Friday")
    fifth_monday = forms.BooleanField(required=False, label="Fifth Monday")
    fifth_tuesday = forms.BooleanField(required=False, label="Fifth Tuesday")
    fifth_wednesday = forms.BooleanField(
        required=False, label="Fifth Wednesday")
    fifth_thursday = forms.BooleanField(required=False, label="Fifth Thursday")
    fifth_friday = forms.BooleanField(required=False, label="Fifth Friday")

    # https://docs.djangoproject.com/en/3.0/topics/forms/modelforms/#changing-the-queryset
    # adapted to change choices instead
    # https://docs.djangoproject.com/en/3.0/ref/models/fields/#field-choices
    # docs for init
    # https://docs.djangoproject.com/en/2.2/_modules/django/forms/forms/#Form
    def __init__(self, *args, **kwargs):
        super(CreateAssignmentForm, self).__init__(*args, **kwargs)
        self.fields["job"].choices = get_job_choices()

    # https://docs.djangoproject.com/en/3.0/ref/forms/validation/#validating-fields-with-clean
    def clean(self):
        data = super().clean()

        try:
            # get the job, ValueError if data isn't an int
            job = Job.objects.get(pk=data.get("job"))

            volunteer = data.get("volunteer")

            # loop over all of the fields
            if hasattr(job, 'route') and job.route.bonusRoute is not None:
                Assignment.objects.get_or_create(
                            job=job,
                            volunteer=volunteer
                        )
            else:
                for field in data:
                    day_of_month = days_of_month_tuples.get(field)

                    # day_of_month must be valid and data[field] must be True to
                    # create
                    if day_of_month and data[field]:
                        # don't attempt to create multiple of same assignment
                        Assignment.objects.get_or_create(
                            job=job,
                            volunteer=volunteer,
                            day_of_week=day_of_month.day_of_week,
                            week_of_month=day_of_month.week_of_month,
                        )

        except (ValueError, Job.DoesNotExist):
                # something in the form was not the correct value
            raise forms.ValidationError("Could not create assignment(s).")

        return data



class EditMultipleAssignmentsForm(forms.Form):
    volunteer = forms.ModelChoiceField(
        queryset=Volunteer.objects.all(),
        widget=autocomplete.ModelSelect2(url="/staff/volunteer-autocomplete"),
        required=False,
    )

    # docs for init
    # https://docs.djangoproject.com/en/2.2/_modules/django/forms/forms/#Form
    def __init__(self, assignments_list, *args, **kwargs):
        # super __init__ don't pass assignments_list or else exception
        self.isBonusRoute = kwargs.pop('isBonusRoute', False)
        super().__init__(*args, **kwargs)
        # need these assignments for validation
        if self.isBonusRoute:
            self.assignments_list = assignments_list
        else:
            self.assignments_list = assignments_list.order_by(
                "week_of_month", "day_of_week")
            for assignment in self.assignments_list:
                label_name = days_of_month_titles[
                    (assignment.day_of_week, assignment.week_of_month)
                ]
                field_name = days_of_month_field_names[
                    (assignment.day_of_week, assignment.week_of_month)
                ]
                self.fields[field_name] = forms.BooleanField(
                    required=False, label=label_name)

    # https://docs.djangoproject.com/en/3.0/ref/forms/validation/#validating-fields-with-clean
    def clean(self):
        data = super().clean()
        # all available assignments are in the fields ('first_monday': True/False).
        # True if selected, False if not
        # self.assignments is used to update the asssignments
        if self.isBonusRoute:
            self.assignments_list[0].volunteer = data.get("volunteer")
            self.assignments_list[0].save()
            return data
        for field in data:
            day_of_month = days_of_month_tuples.get(field)

            # day_of_month must be valid and data[field] must be True to edit
            if day_of_month and data[field]:
                assignment = self.assignments_list.get(
                    day_of_week=day_of_month.day_of_week,
                    week_of_month=day_of_month.week_of_month,
                )
                assignment.volunteer = data.get("volunteer")
                assignment.save()

        return data


class EditSubstitutionForm(ModelForm):
    volunteer = forms.ModelChoiceField(
        queryset=Volunteer.objects.all(),
        widget=autocomplete.ModelSelect2(url="/staff/volunteer-autocomplete"),
        required=False,
    )

    class Meta:
        model = Substitution
        fields = ["volunteer"]


class AnnouncementForm(ModelForm):
    class Meta:
        model = ManagerAnnouncement
        fields = ["display_until", "announcement"]
        widgets = {
            "display_until": DateInput(
                format=("%Y-%m-%d"), attrs={"style": "max-width: 15em"}
            ),
        }


class DateForm(forms.Form):
    date = forms.DateField()


class DateRangeForm(forms.Form):
    begin_date = forms.DateField(
        error_messages={
            "required": "Begin date is required",
            "invalid": "Please enter a valid Begin date",
        }
    )
    end_date = forms.DateField(
        error_messages={
            "required": "End date is required",
            "invalid": "Please enter a valid End date",
        }
    )

    # https://docs.djangoproject.com/en/3.0/ref/forms/validation/#validating-fields-with-clean
    def clean(self):
        data = super().clean()
        begin_date = data.get("begin_date")
        end_date = data.get("end_date")

        if begin_date and end_date:
            if begin_date > end_date:
                raise forms.ValidationError(
                    "Begin date cannot be later than end date")
        return data


class FutureDateRangeForm(forms.Form):
    begin_date = forms.DateField(
        error_messages={
            "required": "Begin date is required",
            "invalid": "Please enter a valid Begin date",
        }
    )
    end_date = forms.DateField(
        error_messages={
            "required": "End date is required",
            "invalid": "Please enter a valid End date",
        }
    )

    # https://docs.djangoproject.com/en/3.0/ref/forms/validation/#validating-fields-with-clean
    def clean(self):
        data = super().clean()
        begin_date = data.get("begin_date")
        end_date = data.get("end_date")

        if begin_date and end_date:
            today = datetime.date.today()
            if begin_date < today or end_date < today:
                raise forms.ValidationError("Dates cannot be historical.")
            if begin_date > end_date:
                raise forms.ValidationError(
                    "Begin date cannot be later than end date")
        return data

class CustomerDateRangeForm(forms.ModelForm):
    class Meta:
        model = DateRange
        fields = ['customer', 'start_date', 'end_date']
        widgets = {
            'customer': autocomplete.ModelSelect2(url="/staff/customer-autocomplete")
        }

class MonthForm(forms.Form):
    month = forms.ChoiceField(choices=list(enumerate(months))[1:])


class SingleDateForm(forms.Form):
    date_picked = forms.DateField()


class CreateSubstitutionForm(forms.Form):
    substitute = forms.ModelChoiceField(
        queryset=Volunteer.objects.all(),
        widget=autocomplete.ModelSelect2(url="/staff/volunteer-autocomplete"),
        required=False,
        error_messages={"invalid_choice": "Please select a valid substitute."},
    )
    job = forms.ChoiceField(
        error_messages={
            "invalid_choice": "Please select a job.",
            "required": "Please select a job.",
        }
    )
    date = forms.DateField(
        required=True,
        error_messages={
            "required": "Please enter a valid date.",
            "invalid": "Please enter a valid date.",
        },
    )
    # assigned volunteer is a ModelChoiceField
    # This allows the values to be cleaned as valid volunteers
    # Open Job has value "" and every other volunteer has value = pk.
    # these values are set in the async function in substitution management
    # this field cannot be required in order to support open job
    assigned_volunteer = forms.ModelChoiceField(
        queryset=Volunteer.objects.all(),
        required=False,
        error_messages={
            "invalid_choice": "Assigned Volunteer was not valid. Please enter a valid date and job, then select an option if needed."
        },
    )

    # https://docs.djangoproject.com/en/3.0/topics/forms/modelforms/#changing-the-queryset
    # adapted to change choices instead
    # https://docs.djangoproject.com/en/3.0/ref/models/fields/#field-choices
    # docs for init
    # https://docs.djangoproject.com/en/2.2/_modules/django/forms/forms/#Form
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["job"].choices = get_job_choices()

    # https://docs.djangoproject.com/en/3.0/ref/forms/validation/#validating-fields-with-clean
    def clean(self):
        data = super().clean()
        # clean and create the substitution
        try:
            day_in_month = date_to_day_of_month(data.get("date"))
            # get the matching assignment
            assignment = Assignment.objects.get(
                day_of_week=day_in_month.day_of_week,
                week_of_month=day_in_month.week_of_month,
                job__pk=data.get("job"),
                volunteer=data.get("assigned_volunteer"),
            )
            # create the substituion object
            Substitution.objects.create(
                assignment=assignment,
                date=data.get("date"),
                volunteer=data.get("substitute"))
        except Assignment.DoesNotExist:
            raise forms.ValidationError(
                "Could not find assignment matching the given job, date, and assigned volunteer. Substitution not created."
            )
        except AttributeError:
            # date was none
            raise forms.ValidationError("Could not create substitution.")

        return data


class VolunteerUserForm(ModelForm):
    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "username",
            "email",
            "is_staff",
        )

    def clean(self):
        data = super().clean()
        cleaned_username = data.get("username")
        # if user did not change their username, don't worry about username
        # validation
        if cleaned_username is None or cleaned_username == "":
            raise forms.ValidationError("Username not valid.")

        if self.instance.username == cleaned_username:
            return data

        # ensure that username is incase sensitive and unique
        try:
            get_user_model()._default_manager.get(username__iexact=cleaned_username)
        except get_user_model().DoesNotExist:
            data["username"] = cleaned_username.lower()
            return data
        raise forms.ValidationError("This username already exists.")
