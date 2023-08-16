from datetime import date

from django import forms
from django.contrib.admin.widgets import AdminDateWidget


class CustomerForm(forms.ModelForm):
    """
    Form for Customer model.
    Join date and end date could range from 1977 to ten years from today.
    Birth date could range from 117 years ago to today.
    """

    class Meta:
        model = Customer
        fields = [
            "join_date",
            "pays",
            "active",
            "first_name",
            "last_name",
            "address",
            "city",
            "state",
            "zip",
            "phone",
            "printed_notes",
            "place_of_worship",
            "birth_date",
            "death_date",
            "sex",
            "contact",
            "contact_phone",
            "diet",
            "cold_diet_restrictions",
            "hot_diet_restrictions",
            "pet",
            "petfood",
            "end_date",
            "referred",
            "ref_phone",
            "bill_to",
            "notes",
            "num_weekend_meals",
            #'location', 'recurrences',
        ]
        labels = {
            "petfood": "Pet Food",
            "num_weekend_meals": "Number of Weekend Meals"}

        # Let the year range for join_date range from 1977 to today.
        # Let the year range for birth_date range from 117 years ago to today.
        widgets = {
            "join_date": SelectDateWidget(
                years=range(
                    1977,
                    date.today().year + 1)),
            "birth_date": SelectDateWidget(
                years=range(
                    date.today().year - 117,
                    date.today().year + 1)),
            "death_date": SelectDateWidget(
                years=range(
                    date.today().year - 117,
                    date.today().year + 1)),
            "end_date": SelectDateWidget(
                years=range(
                    1977,
                    date.today().year + 10),
                empty_label=(
                    "Choose Year",
                    "Choose Month",
                    "Choose Day"),
            ),
        }

    def clean(self):
        """
        Clean method for form of Customer
        Join date could not be later than end date.
        If the Customer is made active through the form post, then the Customer must have
        pays, location, diet and recurrences.
        Also invoke clean method of the Recurrence widget.
        """
        # Check Start vs End Dates
        form_data = self.cleaned_data
        if form_data["end_date"]:
            if form_data["join_date"] > form_data["end_date"]:
                self._errors["join_date"] = [
                    "Start date cannot be later than end date"]
        if form_data["death_date"]:
            if form_data["birth_date"] > form_data["death_date"]:
                self._errors["death_date"] = [
                    "Please enter a valid birth date and death date"]

        # If user checks active, must have these required fields.
        if form_data["active"]:
            active_errors = []
            if form_data["death_date"]:
                active_errors.append("Must deactivate deceased customer")
            if not form_data["pays"]:
                active_errors.append("Missing payment")
            #            if not form_data['location']:
            #                active_errors.append('Missing location')
            if not form_data["diet"]:
                active_errors.append("Missing diet")
            #            if not form_data['recurrences']:
            #                active_errors.append('Missing recurrence')
            if active_errors != []:
                self._errors["active"] = active_errors


#        recurrences = form_data['recurrences']
#        if recurrences:
#            recurrence_clean(recurrences, self)


class DateRangeForm(forms.ModelForm):
    """
    Form for DateRange model.
    """

    def __init__(self, *args, **kwargs):
        self.customer_id = None
        super(DateRangeForm, self).__init__(*args, **kwargs)

    class Meta:
        model = DateRange
        fields = ["start_date", "end_date"]

        widgets = {
            "start_date": SelectDateWidget,
            "end_date": SelectDateWidget}

    def clean(self):
        """
        Clean method of Form for DateRange model.
        Start date could not be later than end date.
        Overlapping date range exclusion for a customer is not allowed.
        """
        form_data = self.cleaned_data
        if form_data["start_date"] > form_data["end_date"]:
            self._errors["end_date"] = [
                "End date cannot be earlier than start date"]
            del form_data["end_date"]
        elif DateRange.objects.filter(
            customer=self.customer_id,
            start_date__lte=form_data["end_date"],
            end_date__gte=form_data["start_date"],
        ):
            self._errors["end_date"] = [
                "There is already an exclusion overlapping this date range for this customer"
            ]
            del form_data["end_date"]
        return form_data


class LabelDateRangeForm(forms.Form):
    """
    Form for choosing a date rnage for which shows the labels
    """

    start_date = forms.DateField(widget=AdminDateWidget)
    end_date = forms.DateField(widget=AdminDateWidget)
