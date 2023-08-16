from dal import autocomplete
from django import forms
from django.forms import ModelForm
from django.shortcuts import get_object_or_404, reverse
from django.utils.html import format_html

from models.models import Customer, Route
from routes import utility


# class SearchForm(forms.Form):
# 	query = forms.CharField()
class RouteFormNoType(ModelForm):
    """
    For validation of routes in edit job
    """

    class Meta:
        model = Route
        fields = [
            "name",
            "num_vols_required",
            "number",
            "description",
            "family_friendly_route"]
        error_messages = {
            "name": {
                "required": "name is required",
                },
            "number": {
                "required": "route number is required",
                },
            "num_vols_required": {
                "required": "num vols required is required",
                },
        }


class AddCustomerForm(forms.Form):
    """
    form used to add a customer to a route
    """

    # link for future reference
    # https://docs.djangoproject.com/en/3.0/ref/forms/fields/#django.forms.ModelChoiceField

    # not sure what we want to do here to have either all or only ones not
    # assigned show up
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.all(),
        label="Select a Customer to Add",
        error_messages={"required": "customer required"},
        widget=autocomplete.ModelSelect2(url="/staff/customer-autocomplete"),
    )
    route = forms.ModelChoiceField(
        queryset=Route.objects.all(), error_messages={
            "required": "route required"})

    def clean(self):
        """
        clean the data in the form, then add to a route
        """
        data = super().clean()
        # missing data is handled
        customer = data.get("customer")
        route = data.get("route")

        # these are None if they do not exist
        if customer is not None and route is not None:
            if customer.route:
                # right now we won't allow for customers to get added
                # without being taken off of old route
                if customer.route == route:
                    self.add_error("customer",
                                   "This customer is already on this route!")
                else:
                    # https://docs.djangoproject.com/en/3.0/ref/utils/#django.utils.html.format_html
                    # https://docs.djangoproject.com/en/3.0/ref/urlresolvers/#reverse
                    # https://stackoverflow.com/questions/40886048/how-to-put-a-link-into-a-django-error-message
                    self.add_error(
                        "customer", format_html(
                            'This customer is already on a route named <a href="{}">{}</a>. Click to <a href="{}">remove and add to this route</a>.'.format(
                                reverse(
                                    "routes:view_route", args=[
                                        customer.route.number]), customer.route.name, reverse(
                                    "routes:add_and_remove_customer_from_route", args=[
                                        customer.pk, route.number], ), )), )
                return data

            # order is zero indexed so we need the total number of
            # customers on the route to know what to set it as
            utility.add_customer_to_route(customer, route)
        return data
