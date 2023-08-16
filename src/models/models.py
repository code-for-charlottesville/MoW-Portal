"""
All the models in one place!

Don't you dare put any forms in here.

TODO:
 - make sure max_lengths match with old portal

"""


from collections import namedtuple
from datetime import date, datetime, timedelta
from operator import mod

from address.models import AddressField
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q, Value
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from recurrence import serialize
from recurrence.fields import RecurrenceField
import usaddress

import interfaces.address_lookup
from interfaces.recurrence import (
    FR,
    MO,
    TH,
    TU,
    WE,
    WEEKLY,
    DayOfMonth,
    Recurrence,
    Rule,
    date_to_day_of_month,
    day_of_month_to_date,
    days_of_week,
    is_friday,
    is_weekend,
    weeks_of_month,
)
from meals.constants import RRULE_COUNT, RRULE_START

NO_FILTER_SENTINAL = "NOFILTER"


Actual = namedtuple(
    "Actual", [
        "volunteer", "job", "date", "original", "is_substitution"])


def actual_dict_to_namedtuple(actual):
    try:
        vol = Volunteer.objects.get(pk=actual["actual_volunteer"])
    except Volunteer.DoesNotExist:
        vol = None
    try:
        job = Job.objects.get(pk=actual["actual_job"])
    except Job.DoesNotExist:
        job = None
    try:
        original = Volunteer.objects.get(pk=actual["actual_original"])
    except Volunteer.DoesNotExist:
        original = None
    return Actual(
        vol,
        job,
        actual["actual_date"],
        original,
        actual["actual_is_substitution"])


## ----- Volunteers ----- ##


class Volunteer(models.Model):
    """
    Model for meals volunteers
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    organization = models.CharField(max_length=100, default="", blank=True)
    address = AddressField(null=True, blank=True, on_delete=models.PROTECT)
    home_phone = models.CharField(
        max_length=50,
        default="",
        blank=True)  # Home Phone
    cell_phone = models.CharField(max_length=50, default="", blank=True)
    work_phone = models.CharField(max_length=50, default="", blank=True)
    birth_date = models.DateField(null=True, blank=True)
    notes = models.TextField(default="", blank=True)
    join_date = models.DateField(default=date.today)
    number_of_people = models.IntegerField(default=1)
    dont_email = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

    class Meta:
        ordering = ["user__last_name", "user__first_name"]


@receiver(post_save, sender=User)
def make_vol(sender, instance, created, **kwargs):
    if created:
        Volunteer.objects.create(user=instance, address="")


@receiver(post_delete, sender=Volunteer)
def delete_user(sender, instance, **kwargs):
    instance.user.delete()


@receiver(pre_save, sender=User)
def lower_username(sender, instance, **kwargs):
    instance.username = instance.username.lower()


class JobType(models.Model):
    name = models.CharField(max_length=100, unique=True, blank=False)

    def __str__(self):
        return self.name

    def strip_space_in_name(self):
        """
        Return the name with spaces stripped out
        """
        return self.name.replace(" ", "_")

    class Meta:
        ordering = ["name"]


class Job(models.Model):
    name = models.CharField(max_length=100, unique=True, blank=False)
    num_vols_required = models.SmallIntegerField(default=1, blank=False)
    recurrence = RecurrenceField(include_dtstart=False)
    job_type = models.ForeignKey(
        JobType,
        on_delete=models.PROTECT,
        null=False,
        blank=False)

    def __str__(self):
        return self.name

    def get_route_pk(self):
        """
        Return the pk of the underlying route or -1 if this job is not a route.
        """
        try:
            route = self.route
            return route.pk
        except Job.DoesNotExist as e:
            return -1

    def get_route_number(self):
        """
        Return the number of the underlying route or -1 if this job is not a route.
        """
        try:
            route = self.route
            return route.number
        except Job.DoesNotExist as e:
            return -1

    def strip_space_in_name(self):
        """
        Return the name with spaces stripped out
        """
        return self.name.replace(" ", "_")

    class Meta:
        ordering = ["route__number", "job_type", "name"]


class Route(Job):
    description = models.TextField(blank=True)
    number = models.IntegerField(unique=True, blank=False)
    bonusRoute = models.OneToOneField('self', on_delete=models.CASCADE, null=True, blank=True)
    # stops = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='stop')
    family_friendly_route = models.BooleanField(default=True)


    class Meta:
        ordering = ["number"]



class Assignment(models.Model):
    """
    Recurring Assignments
        day_of_month (date recurrence eg. first monday, second Tuesday)
        volunteer (FK)
        job (FK)

    HOW OPEN ROUTE WORKS:
        Before, "Open Route" was a magic volunteer user used to allow substitutions on
        days with no recurring assignments.

        Now, a NULL volunteer slot in the recurrences table means that this route needs
        to be substitued - an OPEN ROUTE.
        If there is NO entry for a given day on the month in this table, the route simply
        does not run on this day.
    """

    volunteer = models.ForeignKey(
        Volunteer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True)
    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        null=False,
        blank=False)

    day_of_week = models.SmallIntegerField(choices=((x, days_of_week[x]) for x in range(1, 8)), null=True)
    week_of_month = models.SmallIntegerField(choices=((x, weeks_of_month[x]) for x in range(1, 6)), null=True)

    @staticmethod
    def actuals(
        start_date,
        end_date=None,
        *,
        volunteer=NO_FILTER_SENTINAL,
        original=NO_FILTER_SENTINAL,
        job=NO_FILTER_SENTINAL,
        order_by=None,
        exclude_unfilled=False,
    ):
        """
        This static functions should be called on "Assignment", similar to how
        .objects is accessed on Assignment. However, unlike .objects, this does not
        actually return a queryset. Instead, this returns a lazily evaluated iterable
        of namedtuples, Actuals. Actuals represent what is actually happenning with a job
        on a day, including who is volunteering for that job and who the orignal volunteer
        is. This method respects unsubstituted assignments, substituted assignments, and
        historical data.

        Because this function does not return a queryset, it cannot be filtered like one.
        To filter the results, filters must be passed into the call to Assignment.actuals().
        For example, a date must be suplied. If only one date is supplied, the actuals are
        computed for that date only. If another date is supplied, the actuals for the dates
        between start_date and end_date are computed. end_date is exclusive.
        Additional filters can be provided, volunteer, original, and job. Note that, right now,
        only equality filters are supported. For example, a job__job_type= filter is not
        currently possible.

        A note on filtering by volunteer=None and original=None: cases where this is true:
         - Open Route Assignments
         - Unfilled Substitution requests for Open Route Assignments
         - Volunteer Records where a Volunteer has since been deleted
        This is why there is an additional field, is_substitution. In the case of an Open Route
        Assignment, is_substitution will be False. If the actual is an unfilled substitution
        request for an Open Route, is_substitution will be True. If the actual is a record, but
        a volunteer has been set to None, is_substitution will be whatever it started as.
        Also note that in the case of an unfilled substitution request for an open job, only
        the substitution request will be returned.

        Note: Please do not try to implement this logic yourself. This function has been heavily
        tested, and it's important that the whole app is consistent in how actuals are computed.
        """
        if order_by:
            if isinstance(order_by, str):
                order_by = (order_by,)
        else:
            order_by = ()
        allowed_order_bys = ("volunteer", "job", "date")
        for o in order_by:
            if o not in allowed_order_bys:
                raise ValueError(
                    f"""Unsupported order_by, {o}.
Can only order by {", ".join(allowed_order_bys)}"""
                )

        today = date.today()
        end_date = end_date or start_date + timedelta(days=1)
        start_date = date(
            year=start_date.year,
            month=start_date.month,
            day=start_date.day)
        end_date = date(
            year=end_date.year,
            month=end_date.month,
            day=end_date.day)

        assignment_filters = Q()
        substitute_filters = Q()
        record_filters = Q()
        if volunteer != NO_FILTER_SENTINAL:
            assignment_filters &= Q(volunteer=volunteer)
            substitute_filters &= Q(volunteer=volunteer)
            record_filters &= Q(volunteer=volunteer)
        if original != NO_FILTER_SENTINAL:
            assignment_filters &= Q(volunteer=original)
            substitute_filters &= Q(assignment__volunteer=original)
            record_filters &= Q(original=original)
        if job != NO_FILTER_SENTINAL:
            assignment_filters &= Q(job=job)
            substitute_filters &= Q(assignment__job=job)
            record_filters &= Q(job=job)

        exclusor = {"volunteer": None} if exclude_unfilled else {}

        assignment_values = dict(
            #  actual_date=Value(day, output_field=models.DateField()),  handled in loop
            actual_volunteer=F("volunteer"),
            actual_job=F("job"),
            actual_original=F("volunteer"),
            actual_is_substitution=Value(False, models.BooleanField()),
        )
        substitute_values = dict(
            actual_date=F("date"),
            actual_volunteer=F("volunteer"),
            actual_job=F("assignment__job"),
            actual_original=F("assignment__volunteer"),
            actual_is_substitution=Value(True, models.BooleanField()),
        )
        record_values = dict(
            actual_date=F("date"),
            actual_volunteer=F("volunteer"),
            actual_job=F("job"),
            actual_original=F("original"),
            actual_is_substitution=F("is_substitution"),
        )
        if "volunteer" in order_by:
            for vals in (assignment_values, substitute_values, record_values):
                vals.update(
                    volunteer_last_name=F("volunteer__user__last_name"),
                    volunteer_first_name=F("volunteer__user__first_name"),
                )
        if "job" in order_by:
            for vals in (assignment_values, record_values):
                vals.update(
                    job_type=F("job__job_type__name"),
                    route_number=F("job__route__number"),
                    name=F("job__name"),
                )
            substitute_values.update(
                job_type=F("assignment__job__job_type__name"),
                route_number=F("assignment__job__route__number"),
                name=F("assignment__job__name"),
            )

        assignments = []
        day = max(start_date, today)

        # used in loop below to add bonus route assignments
        bonusRouteAssignments = Assignment.objects.filter(
                    day_of_week=None,
                    week_of_month=None) .filter(assignment_filters) .exclude(
                    **exclusor)


        while day < end_date:
            dom = date_to_day_of_month(day)
            exclusionary_subs = Substitution.objects.filter(
                date=day).values_list("assignment_id")
            days_assignments = (
                Assignment.objects.filter(
                    day_of_week=dom.day_of_week,
                    week_of_month=dom.week_of_month) .filter(assignment_filters) .exclude(
                    id__in=exclusionary_subs) .exclude(
                    **exclusor) .values(
                    actual_date=Value(
                        day,
                        output_field=models.DateField()),
                    **assignment_values,
                ))
            assignments.append(days_assignments)

            for brAssignment in bonusRouteAssignments:
                bonusRouteDay = datetime(year=day.year, month=day.month, day = day.day)
                if brAssignment.job.recurrence.after(bonusRouteDay, inc=True, dtstart=bonusRouteDay) == bonusRouteDay:
                    bonusRouteActual = Assignment.objects.filter(id=brAssignment.id).values(
                    actual_date=Value(
                        day,
                        output_field=models.DateField()),
                    **assignment_values,
                    )
                    assignments.append(bonusRouteActual)
            day += timedelta(days=1)

        subs = (
            Substitution.objects.filter(
                date__gte=max(
                    start_date,
                    today),
                date__lt=end_date) .filter(substitute_filters) .exclude(
                **exclusor) .values(
                    **substitute_values))
        past = (
            VolunteerRecord.objects.filter(
                date__gte=start_date,
                date__lt=date.today()) .filter(record_filters) .values(
                **record_values))  # Don't exclude Nones, they are deleted vols
        result = past.union(subs, *assignments)

        new_order_by = []
        for o in order_by:
            if o == "volunteer":
                new_order_by.append("volunteer_last_name")
                new_order_by.append("volunteer_first_name")
            elif o == "date":
                new_order_by.append("actual_date")
            elif o == "job":
                new_order_by.append("route_number")
                new_order_by.append("job_type")
                new_order_by.append("name")

        result = result.order_by(*new_order_by)
        return map(actual_dict_to_namedtuple, result)

    def to_day_of_month(self):
        return DayOfMonth(
            day_of_week=self.day_of_week,
            week_of_month=self.week_of_month)

    def get_day_of_month_str(self):
        return str(self.to_day_of_month())

    # eg. third monday, first tuesday, second thursday, up to fifth

    def __str__(self):
        if self.day_of_week is None and self.week_of_month is None:
            return f"{self.volunteer} is volunteering for {self.job} which is a Bonus Pantry Route"
        day_of_month = self.get_day_of_month_str()
        return f"{self.volunteer} is volunteering for {self.job} on the {day_of_month}"

    class Meta:
        unique_together = ["job", "volunteer", "day_of_week", "week_of_month"]


class Substitution(models.Model):
    """
    Substitutions
        date (specific date eg. 10/13/2019)
        volunteer (FK)
        job (FK)

    HOW UNFILLED SUBS WORK:
        Before, there were seperate tables for unfilled and filled subsitutions
        (SubstitionRequest and Substitution respectively).

        Now, a NULL volunteer in a substitution represents an unfilled substitution.

    TODO:
     - Validate that Substitutions are not for a Job that has no Assignment.
        Lack of a Assignment for a Job on a certain day means that no volunteers
        are need for that job at that time.
        Note that it is OK to have a Substitution for a Job and Assignment that
        has a NULL volunteer since this is an OPEN ROUTE.
    """

    volunteer = models.ForeignKey(
        Volunteer,
        related_name="volunteer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        null=True,
        blank=True)
    date = models.DateField(null=False, blank=False)

    def clean(self):
        sub = self
        super().clean()
        year = sub.date.year
        month = sub.date.month
        day_of_month = sub.assignment.to_day_of_month()
        recurring_date = day_of_month_to_date(day_of_month, month, year)
        if recurring_date != sub.date:
            raise ValidationError(
                f"Cannot substitute on {sub.date} for {sub.assignment.job} on {day_of_month}.",
                params={
                    "value": sub},
            )
        if self.volunteer == self.assignment.volunteer:
            raise ValidationError("Volunteer and Requester cannot be the same")

    class Meta:
        unique_together = ["volunteer", "assignment", "date"]


## ----- Customers ----- ##


class Diet(models.Model):
    """
    Model for handling different diets for Customer model.
    A foreign key for Customer model.
    """

    name = models.CharField(max_length=100, default="")
    code = models.CharField(max_length=5, default="")

    def __str__(self):
        return self.name


class Pet(models.Model):
    """
    Model for handling pets for Customer model.
    A foreign key for Customer model.
    """

    name = models.CharField(max_length=100, default="")

    def __str__(self):
        return self.name


class PetFood(models.Model):
    """
    Model for handling pet foods for Customer model.
    A foreign key for Customer model.
    """

    name = models.CharField(max_length=100, default="")
    code = models.CharField(max_length=5, default="")

    def __str__(self):
        return self.name


class Payment(models.Model):
    """
    Model for handling different payments for Customer Model.
    A foreign key for Customer model.
    """

    name = models.CharField(max_length=100, default="")

    def __str__(self):
        return self.name


# make sure the defaults for impairments ensure that if something screws
# up with overriding default doesn't get someone dead
class Customer(models.Model):
    """
    Model for Customer.

    name and address and birthdate are only required fields, everything else is nullable
    """

    # route = models.CharField(db_index=True, max_length=100, default="")
    route = models.ForeignKey(
        Route,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customer')
    historical_route = models.CharField(max_length=100, default="", blank=True)

    join_date = models.DateField(default=date.today)

    # MOW, self pay, partial pay, JABA, blue ridge pace (pace)
    pays = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True)
    active = models.BooleanField(default=False)
    first_name = models.CharField(db_index=True, max_length=100, default="")
    last_name = models.CharField(db_index=True, max_length=100, default="")
    address = AddressField(blank=True, on_delete=models.PROTECT)
    phone = models.CharField(max_length=50, default="", blank=True)

    # difference between this and notes? landmarks gets put on the printout
    printed_notes = models.TextField(default="", blank=True)
    birth_date = models.DateField(null=True)
    sex = models.CharField(max_length=50, default="", blank=True)
    contact = models.CharField(max_length=200, default="", blank=True)
    contact_phone = models.CharField(max_length=50, default="", blank=True)
    diet = models.ForeignKey(
        Diet,
        on_delete=models.SET_NULL,
        null=True,
        blank=True)

    # these are allergies (dietary preferences)
    cold_diet_restrictions = models.CharField(
        max_length=200, default="", blank=True)
    hot_diet_restrictions = models.CharField(
        max_length=200, default="", blank=True)
    pet = models.ForeignKey(
        Pet,
        on_delete=models.SET_NULL,
        null=True,
        blank=True)
    petfood = models.ForeignKey(
        PetFood,
        on_delete=models.SET_NULL,
        null=True,
        blank=True)

    # TODO: should be updated when active is unchecked?
    end_date = models.DateField(null=True, blank=True)
    end_reason = models.CharField(max_length=200, null=True, blank=True)

    referred = models.CharField(
        max_length=200,
        default="",
        blank=True)  # a referral person
    ref_phone = models.CharField(max_length=50, default="", blank=True)
    bill_to = models.CharField(max_length=200, default="", blank=True)
    notes = models.TextField(default="", blank=True)
    meal_recurrence = RecurrenceField(default="", null=True, blank=True)
    num_weekend_meals = models.PositiveIntegerField(default=0)
    dont_email = models.BooleanField(default=False)
    lat = models.FloatField(default=0, blank=True, null=True)
    lon = models.FloatField(default=0, blank=True, null=True)
    receivesBonusPantryDelivery = models.BooleanField("Receives Bonus Pantry Delivery", default=True, null=False)

    class Meta:
        order_with_respect_to = "route"
        unique_together = [
            "first_name",
            "last_name",
            "contact",
            "contact_phone"]

    def clean(self):
        """
        Clean method for Customer class.
        Make sure that if the customer is active and assigned to a route, the user will be removed from their route.
        """
        if not self.active and self.route is not None:
            self.route = None

    def __str__(self):
        return self.first_name + " " + self.last_name

    def get_parsed_address(self):
        try:
            parsedAddress, addressType = usaddress.tag(address_string=self.address.raw, tag_mapping={
            'AddressNumber': 'address1',
            'AddressNumberPrefix': 'address1',
            'AddressNumberSuffix': 'address1',
            'StreetName': 'address1',
            'StreetNamePreDirectional': 'address1',
            'StreetNamePreModifier': 'address1',
            'StreetNamePreType': 'address1',
            'StreetNamePostDirectional': 'address1',
            'StreetNamePostModifier': 'address1',
            'StreetNamePostType': 'address1',
            'CornerOf': 'address1',
            'IntersectionSeparator': 'address1',
            'LandmarkName': 'address1',
            'USPSBoxGroupID': 'address1',
            'USPSBoxGroupType': 'address1',
            'USPSBoxID': 'address1',
            'USPSBoxType': 'address1',
            'BuildingName': 'address1',
            'OccupancyType': 'address1',
            'OccupancyIdentifier': 'address1',
            'SubaddressIdentifier': 'address1',
            'SubaddressType': 'address1',
            'PlaceName': 'address2',
            'StateName': 'address2',
            'ZipCode': 'address2',
        })
        except usaddress.RepeatedLabelError:
            parsedAddress = {'address1': self.address.raw}
        return parsedAddress

    def get_birthdate(self):
        return str(self.birth_date.strftime("%b")) + \
            " " + str(self.birth_date.day)

    def num_meals_on_day(self, day):
        """
        Return the number of meals on a specific day
        """
        day = date(year=day.year, month=day.month, day=day.day)
        if is_weekend(day):
            return 0

        if day < date.today():  # Strict less-than VERY import here. Otherwise recursion!
            try:
                record = CustomerRecord.objects.get(date=day, customer=self)
            except CustomerRecord.DoesNotExist:
                return 0
            return record.num_meals
        if not self.active:
            return False
        dt = datetime(
            year=day.year,
            month=day.month,
            day=day.day,
            hour=0,
            minute=0,
            second=0)
        possible_match = self.meal_recurrence.between(
            dt,
            dt,
            dtstart=dt -
            timedelta(
                days=1),
            dtend=dt +
            timedelta(
                days=1),
            inc=True,
        )
        if len(possible_match) == 0 or self.date_range_excluded(dt):
            return 0

        return 1 + (self.num_weekend_meals if is_friday(day) else 0)

    def receives_meal_on_date(self, day):
        """
        Return the number of meals on a specific day
        """
        if is_weekend(day):
            return False
        if not self.active:
            return False
        dt = datetime(
            year=day.year,
            month=day.month,
            day=day.day,
            hour=0,
            minute=0,
            second=0)
        possible_match = self.meal_recurrence.between(
            dt,
            dt,
            dtstart=dt -
            timedelta(
                days=1),
            dtend=dt +
            timedelta(
                days=1),
            inc=True,
        )
        if len(possible_match) == 0 or self.date_range_excluded(dt):
            return False
        return True

    def date_range_excluded(self, dt):
        return DateRange.objects.filter(
            customer=self, start_date__lte=dt, end_date__gte=dt
        ).exists()


@receiver(pre_save, sender=Customer)
def find_lat_lon(sender, instance, **kwargs):
    if kwargs["raw"]:
        return
    geom = interfaces.address_lookup.validate(instance.address)
    instance.lat = geom["lat"]
    instance.lon = geom["lng"]


# a date range for excluding recurrence
class DateRange(models.Model):
    """
    Date range model for excluding recurrence of Customer.
    """

    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE
    )  # if a route gets deleted, delete any DateRanges that it has
    # start and end date are inclusive, start_date == end_date if it's just
    # one day
    start_date = models.DateField(default=date.today)
    end_date = models.DateField(default=date.today)

    def __str__(self):
        """
        ToString method for the DateRange model.
        :return: a string that describes the date range excluding recurrence for a Customer.
        """
        return "%s won't get meals from %s to %s" % (
            str(self.customer),
            str(self.start_date),
            str(self.end_date),
        )

class Run(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    run_date = models.DateField()
    delivery_status = models.CharField(max_length=50, null=True)
    customer_status = models.CharField(max_length=50, null=True)
    notes = models.CharField(max_length=250, null=True)

    @property
    def feedback_provided(self):
        return not(self.delivery_status is None and self.customer_status is None and self.notes is None)
    class Meta():
            constraints = (models.UniqueConstraint(fields=['customer', 'run_date'], name='customer_rundate'),)


## ----- Other ----- ##


class ManagerAnnouncement(models.Model):
    created_by = models.ForeignKey(
        Volunteer, on_delete=models.PROTECT, null=True)
    display_until = models.DateField(null=True, blank=False)
    date_created = models.DateField(
        default=date.today, editable=False, blank=False, null=False
    )
    announcement = models.TextField(default="", blank=False)

    def __str__(self):
        return self.announcement


class CustomerRecord(models.Model):
    """
    This model serves as the record-keeping for delivered meals
    It is primarily used for the Daily/Monthly Billing Reports
    """

    # TODO deal w on_delete properly
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        default=None,
        null=True)
    date = models.DateField(default=date.today)
    num_meals = models.IntegerField()
    payment_type = models.ForeignKey(
        Payment, on_delete=models.SET_NULL, default=None, null=True
    )
    route_assigned = models.ForeignKey(
        Route, on_delete=models.SET_NULL, default=None, null=True
    )

    class Meta:
        unique_together = ["customer", "date"]


class VolunteerRecord(models.Model):
    """
    This serves to record-keep volunteers and what jobs they actually did
    """

    volunteer = models.ForeignKey(
        Volunteer,
        related_name="record",
        on_delete=models.SET_NULL,
        default=None,
        null=True)
    job = models.ForeignKey(
        Job,
        on_delete=models.SET_NULL,
        default=None,
        null=True)
    date = models.DateField(default=date.today)
    original = models.ForeignKey(
        Volunteer,
        on_delete=models.SET_NULL,
        default=None,
        null=True)
    is_substitution = models.BooleanField()

    class Meta:
        unique_together = ["volunteer", "job", "date"]
