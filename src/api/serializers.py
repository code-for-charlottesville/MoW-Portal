from datetime import date, datetime, timedelta, timezone
from rest_framework import serializers
from models.models import Assignment, Customer, ManagerAnnouncement, Route, Run, Volunteer, Job, Substitution
from api.myJobs.myJobsView import MyJobsViewSet
from django.contrib.auth.models import User
import address



#Address Serializers. https://github.com/furious-luke/django-address
class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = address.models.Country
        fields = ('name', 'code')


class StateSerializer(serializers.ModelSerializer):
    country = CountrySerializer()

    class Meta:
        model = address.models.State
        fields = ('name', 'code', 'country')

class LocalitySerializer(serializers.ModelSerializer):
    state = StateSerializer()
    postalCode = serializers.CharField(source='postal_code')

    class Meta:
        model = address.models.Locality
        fields = (
            'name',
            'state',
            'postalCode'
        )


class AddressSerializer(serializers.ModelSerializer):
    locality = LocalitySerializer()

    class Meta:
        model = address.models.Address
        fields = (
            'raw',
            'street_number',
            'route',
            'locality'
        )
#Customer Serializers
class CustomerSerializer(serializers.ModelSerializer):
    #remap field names to remove underscore
    customerId = serializers.IntegerField(source='id')
    firstName = serializers.CharField(source='first_name')
    lastName = serializers.CharField(source='last_name')
    printedNotes = serializers.CharField(source='printed_notes')
    address = AddressSerializer()
    formattedAddress = serializers.SerializerMethodField(read_only=True)


    def get_formattedAddress(self, obj):
        return obj.get_parsed_address()

    class Meta:
        model = Customer
        fields = (
            'customerId',
            'firstName',
            'lastName',
            'printedNotes',
            'formattedAddress',
            'address'
        )

#Auth serializers. Custom auth serializer allows us to rename and use only certain fields that the app needs.
class UserSerializer(serializers.ModelSerializer):
    userId = serializers.CharField(source='pk')
    firstName = serializers.CharField(source='first_name')
    lastName = serializers.CharField(source='last_name')

    class Meta:
        model = User
        fields = ('userId', 'username', 'email', 'firstName', 'lastName')


#Annoucements serializers
class AnnouncementSerializer(serializers.ModelSerializer):
    #rename some fields
    displayUntil = serializers.CharField(source='display_until')
    created = serializers.CharField(source='date_created')

    class Meta:
        model = ManagerAnnouncement
        fields = ("id", "created_by", "displayUntil", "created", "announcement")

class RunSerializer(serializers.ModelSerializer):
    customer = serializers.IntegerField(source='customer.id')
    feedback_provided = serializers.BooleanField()
    class Meta():
        model = Run
        fields = ('customer', 'feedback_provided')

class MyJobSerializer(serializers.Serializer):
    routeNumber = serializers.CharField()
    jobId = serializers.IntegerField()
    jobName = serializers.CharField()
    jobType = serializers.CharField()
    volunteerId = serializers.IntegerField()
    date_yyyy_mm_dd = serializers.DateField(source='date')
    isSub = serializers.BooleanField()

    class Meta():
        model = MyJobsViewSet.Job
        fields = ['routeNumber', 'jobId', 'jobName', 'jobType', 'volunteerId', 'date_yyyy_mm_dd', 'isSub']

class RouteOverviewSerializer(serializers.ModelSerializer):

    customers = serializers.SerializerMethodField(read_only=True)

    def get_customers(self, obj):
        if str(obj.job_type) == 'Bonus Delivery':
            customers = obj.bonusRoute.customer.all()
            return CustomerSerializer(customers, many=True).data
        else:
            customers = obj.customer.all()
            customers_receiving_meal = [customer for customer in customers if customer.receives_meal_on_date(self.context)]
            return CustomerSerializer(customers_receiving_meal, many=True).data
    class Meta():
        model = Route
        fields = [ 'name', 'number', 'description', 'customers' ]
