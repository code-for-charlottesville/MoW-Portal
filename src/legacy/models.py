from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.transaction import TransactionManagementError
from django.db.utils import IntegrityError
from recurrence import deserialize

from interfaces.recurrence import (
    MONTHLY,
    WEEKLY,
    DayOfMonth,
    date_to_day_of_month,
    split_recurrence,
)
from meals.constants import (
    MOW_LAT,
    MOW_LON,
    PACKER_COLD,
    PACKER_HOT,
    PACKER_TYPE_NAME,
    ROUTE_TYPE_NAME,
    SHUTTLE_TYPE_NAME,
    VOLS_PER_COLD,
    VOLS_PER_HOT,
)
from models.models import *
from staff.forms import AddressForm

LEGACY_OPENROUTE_USERNAME = "OPEN_ROUTE"


class EasyImportMixin:
    """
    Works if the model has no foreign keys and is exactly the same as our model
    """

    def _import(self):
        classname = self.__class__.__name__
        our_model = globals()[classname[len("Legacy"):]]
        fieldnames = [x.name for x in self.__class__._meta.fields]
        kwargs = {field: getattr(self, field) for field in fieldnames}
        del kwargs["id"]
        our_model.objects.create(**kwargs)


class LegacyUser(EasyImportMixin, models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.BooleanField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.CharField(max_length=254)
    is_staff = models.BooleanField()
    is_active = models.BooleanField()
    date_joined = models.DateTimeField()

    def _import(self):
        if self.username != "OPEN_ROUTE":
            return super()._import()


class LegacyRoute(models.Model):
    route = models.IntegerField()
    calendarId = models.CharField(db_column="calendarId", max_length=200)
    description = models.CharField(max_length=400)

    def _import(self):
        route_type, _ = JobType.objects.get_or_create(name=ROUTE_TYPE_NAME)
        Route.objects.create(
            name=f"Route {self.route}",
            number=self.route,
            description=self.description,
            job_type=route_type,
        )


class LegacyDiet(EasyImportMixin, models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=5)


class LegacyPayment(EasyImportMixin, models.Model):
    name = models.CharField(max_length=100)


class LegacyPet(EasyImportMixin, models.Model):
    name = models.CharField(max_length=100)


class LegacyPetFood(EasyImportMixin, models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=5)


class LegacyDjangoContentType(models.Model):
    """Don't import"""

    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)


class LegacyDjangoAdminLog(models.Model):
    """Don't import"""

    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.SmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey(
        LegacyDjangoContentType, models.DO_NOTHING, blank=True, null=True
    )
    user = models.ForeignKey(LegacyUser, models.DO_NOTHING)


class LegacyDjangoMigrations(models.Model):
    """Don't import"""

    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()


class LegacyDjangoSession(models.Model):
    """Don't import"""

    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()


class LegacyDjangoSite(models.Model):
    """Don't import"""

    domain = models.CharField(unique=True, max_length=100)
    name = models.CharField(max_length=50)


class LegacyGroup(models.Model):
    """Don't import"""

    name = models.CharField(unique=True, max_length=80)


class LegacyPermission(models.Model):
    """Don't import"""

    name = models.CharField(max_length=255)
    content_type = models.ForeignKey(
        LegacyDjangoContentType, models.DO_NOTHING)
    codename = models.CharField(max_length=100)


class LegacyGroupPermissions(models.Model):
    """Don't import"""

    group = models.ForeignKey(LegacyGroup, models.DO_NOTHING)
    permission = models.ForeignKey(LegacyPermission, models.DO_NOTHING)


class LegacyUserGroups(models.Model):
    """Don't import"""

    user = models.ForeignKey(LegacyUser, models.DO_NOTHING)
    group = models.ForeignKey(LegacyGroup, models.DO_NOTHING)


# class LegacyUserUserPermissions(models.Model):
#     user = models.ForeignKey(LegacyUser, models.DO_NOTHING)
#     permission = models.ForeignKey(LegacyPermission, models.DO_NOTHING)


class LegacyAccessattempt(models.Model):
    """Don't import"""

    user_agent = models.CharField(max_length=255)
    ip_address = models.CharField(max_length=39, blank=True, null=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    trusted = models.IntegerField()
    http_accept = models.CharField(max_length=1025)
    path_info = models.CharField(max_length=255)
    attempt_time = models.DateTimeField()
    get_data = models.TextField()
    post_data = models.TextField()
    failures_since_start = models.IntegerField()


class LegacyAccesslog(models.Model):
    """Don't import"""

    user_agent = models.CharField(max_length=255)
    ip_address = models.CharField(max_length=39, blank=True, null=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    trusted = models.IntegerField()
    http_accept = models.CharField(max_length=1025)
    path_info = models.CharField(max_length=255)
    attempt_time = models.DateTimeField()
    logout_time = models.DateTimeField(blank=True, null=True)


class LegacyCustomer(models.Model):
    route_order = models.IntegerField()
    join_date = models.DateField()
    active = models.IntegerField()
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    address = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip = models.CharField(max_length=100)
    phone = models.CharField(max_length=50)
    printed_notes = models.TextField()
    place_of_worship = models.CharField(max_length=100)
    birth_date = models.DateField(blank=True, null=True)
    sex = models.CharField(max_length=50)
    contact = models.CharField(max_length=200)
    contact_phone = models.CharField(max_length=50)
    doctor = models.CharField(max_length=200)
    hospital = models.CharField(max_length=200)
    cold_diet_restrictions = models.CharField(max_length=200)
    hot_diet_restrictions = models.CharField(max_length=200)
    end_date = models.DateField(blank=True, null=True)
    referred = models.CharField(max_length=200)
    ref_phone = models.CharField(max_length=50)
    agency = models.CharField(max_length=200)
    in_care_of = models.CharField(max_length=200)
    bill_to = models.CharField(max_length=200)
    notes = models.TextField()
    recurrences = models.TextField(blank=True, null=True)
    num_weekend_meals = models.IntegerField()
    location = models.CharField(max_length=42, blank=True, null=True)
    diet = models.ForeignKey(
        LegacyDiet,
        models.DO_NOTHING,
        blank=True,
        null=True)
    pays = models.ForeignKey(
        LegacyPayment,
        models.DO_NOTHING,
        blank=True,
        null=True)
    route = models.ForeignKey(
        LegacyRoute,
        models.DO_NOTHING,
        blank=True,
        null=True)
    death_date = models.DateField(blank=True, null=True)
    pet = models.ForeignKey(
        LegacyPet,
        models.DO_NOTHING,
        blank=True,
        null=True)
    petfood = models.ForeignKey(
        LegacyPetFood,
        models.DO_NOTHING,
        blank=True,
        null=True)

    def _import(self):
        addr_form = AddressForm(
            {"address": f"{self.address}, {self.city}, {self.state}"})
        if addr_form.is_valid():
            our_address = addr_form.cleaned_data["address"]
            our_address.save()
        else:
            return str(form.errors)
        our_diet = (
            Diet.objects.get(
                name=self.diet.name,
                code=self.diet.code) if self.diet else None)
        our_pays = Payment.objects.get(
            name=self.pays.name) if self.pays else None
        our_route = Route.objects.get(
            number=self.route.route) if self.route else None
        our_pet = Pet.objects.get(name=self.pet.name) if self.pet else None
        our_petfood = (
            PetFood.objects.get(name=self.petfood.name, code=self.petfood.code)
            if self.petfood
            else None
        )

        Customer.objects.create(
            join_date=self.join_date,
            active=bool(self.active),
            first_name=self.first_name,
            last_name=self.last_name,
            address=our_address,
            phone=self.phone,
            printed_notes=self.printed_notes,
            birth_date=self.birth_date,
            sex=self.sex,
            contact=self.contact,
            contact_phone=self.contact_phone,
            cold_diet_restrictions=self.cold_diet_restrictions,
            hot_diet_restrictions=self.hot_diet_restrictions,
            end_date=self.end_date,
            referred=self.referred,
            ref_phone=self.ref_phone,
            bill_to=self.bill_to,
            notes=self.notes,
            meal_recurrence=deserialize(self.recurrences),
            num_weekend_meals=self.num_weekend_meals,
            diet=our_diet,
            pays=our_pays,
            route=our_route,
            pet=our_pet,
            petfood=our_petfood,
            lat=MOW_LAT,
            lon=MOW_LON,
        )


class LegacyDateRange(models.Model):
    start_date = models.DateField()
    end_date = models.DateField()
    customer = models.ForeignKey(LegacyCustomer, models.DO_NOTHING)

    def _import(self):

        customer = Customer.objects.get(
            first_name=self.customer.first_name,
            last_name=self.customer.last_name,
            contact=self.customer.contact,
            contact_phone=self.customer.contact_phone,
        )
        # will cause exception on not found or on multiple found

        DateRange.objects.create(
            start_date=self.start_date,
            end_date=self.end_date,
            customer=customer)


class LegacyManagerAnnouncement(models.Model):
    display_until = models.DateField()
    date_created = models.DateField()
    announcement = models.TextField()
    display = models.IntegerField()
    created_by = models.ForeignKey(
        LegacyUser,
        models.DO_NOTHING,
        blank=True,
        null=True)

    def _import(self):
        if self.created_by:
            created_by = Volunteer.objects.get(
                user=User.objects.get(username=self.created_by.username)
            )
        else:
            created_by = None
        ManagerAnnouncement.objects.create(
            display_until=self.display_until,
            date_created=self.date_created,
            announcement=self.announcement,
            created_by=created_by,
        )


class LegacyUserinfo(models.Model):
    """Don't import"""

    calendarid = models.CharField(db_column="calendarId", max_length=200)
    username = models.CharField(max_length=100)


class LegacyDontsendentry(models.Model):
    to_address = models.CharField(max_length=254)
    when_added = models.DateTimeField()

    def _import(self):
        users = User.objects.filter(email=self.to_address)
        custs = Customer.objects.filter(contact=self.to_address)
        if not custs and not users:
            return (
                f"DontSendEntry to {self.to_address} did not match any customers or volunteers"
            )
        for cust in custs:
            cust.dont_email = True
            cust.save()
        for user in users:
            user.volunteer.dont_email = True
            user.volunteer.save()


class LegacyMessage(models.Model):
    """ Not sure what this is -- not importing for now"""

    message_data = models.TextField()
    when_added = models.DateTimeField()
    priority = models.CharField(max_length=1)


class LegacyVolunteer(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    organization = models.CharField(max_length=100)
    address = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip = models.CharField(max_length=100)
    home_phone = models.CharField(max_length=50)
    email = models.CharField(max_length=100)
    cell_phone = models.CharField(max_length=50)
    work_phone = models.CharField(max_length=50)
    birth_date = models.DateField(blank=True, null=True)
    notes = models.TextField()
    join_date = models.DateField()
    user = models.ForeignKey(
        LegacyUser,
        models.DO_NOTHING,
        unique=True,
        blank=True,
        null=True)

    def _import(self):
        if self.user.username == LEGACY_OPENROUTE_USERNAME:
            return "Skipping Open Route"
        vol = Volunteer.objects.get(
            user=User.objects.get(
                username=self.user.username.lower()))
        vol.organization = self.organization
        vol.home_phone = self.home_phone
        vol.cell_phone = self.cell_phone
        vol.work_phone = self.work_phone
        vol.birth_date = self.birth_date
        vol.notes = self.notes
        vol.join_date = self.join_date
        vol.address = ""
        vol.save()
        user = vol.user
        user.first_name = self.first_name
        user.last_name = self.last_name
        user.save()
        try:
            addr_form = AddressForm(
                {"address": f"{self.address}, {self.city}, {self.state}"})
            if addr_form.is_valid():
                our_address = addr_form.cleaned_data["address"]
                our_address.save()
            else:
                return str(form.errors)
            vol.address = our_address
            vol.save()
        except ValidationError:
            return f"address for {self.first_name} ignored"


class LegacyMessagelog(models.Model):
    """ Not sure what this is -- not importing for now"""

    message_data = models.TextField()
    when_added = models.DateTimeField()
    priority = models.CharField(max_length=1)
    when_attempted = models.DateTimeField()
    result = models.CharField(max_length=1)
    log_message = models.TextField()
    message_id = models.TextField(blank=True, null=True)


class LegacyReportday(models.Model):
    date = models.DateField()
    num_meals = models.IntegerField()
    customer = models.ForeignKey(LegacyCustomer, models.DO_NOTHING)

    def _import(self):
        cust = Customer.objects.get(
            first_name=self.customer.first_name,
            last_name=self.customer.last_name,
            contact=self.customer.contact,
            contact_phone=self.customer.contact_phone,
        )
        if self.customer.route:
            route = Route.objects.get(number=self.customer.route.route)
        else:
            route = None
        CustomerRecord.objects.create(
            date=self.date,
            customer=cust,
            num_meals=self.num_meals,
            payment_type=cust.pays,
            route_assigned=route,
        )


class LegacyPackerjob(models.Model):
    name = models.CharField(max_length=100)

    def _import(self):
        lower_name = self.name.lower()
        if "hot" not in lower_name and "cold" not in lower_name:
            return f"{self.name} is neither hot nor cold"

        job, created = Job.objects.get_or_create(
            name=PACKER_HOT if "hot" in lower_name else PACKER_COLD,
            job_type=JobType.objects.get_or_create(name=PACKER_TYPE_NAME)[0],
        )
        if not created:
            return f"Duplicate LegacyPackerJob, {self.name} cannot be imported"


class LegacyVolunteerpackerjob(models.Model):
    """
    Need to split recurrence into many day_of_month
    """

    recurrences = models.TextField()
    packer_job = models.ForeignKey(LegacyPackerjob, models.DO_NOTHING)
    volunteer = models.ForeignKey(LegacyVolunteer, models.DO_NOTHING)

    def _import(self):
        if self.volunteer.user.username == LEGACY_OPENROUTE_USERNAME:
            vol = None
        else:
            vol = Volunteer.objects.get(user=User.objects.get(
                username=self.volunteer.user.username.lower()))
        job = Job.objects.get(
            name=PACKER_HOT if "hot" in self.packer_job.name.lower() else PACKER_COLD)
        for day_of_month in split_recurrence(self.recurrences):
            Assignment.objects.create(
                volunteer=vol,
                job=job,
                day_of_week=day_of_month.day_of_week,
                week_of_month=day_of_month.week_of_month,
            )
            now_assigned = Assignment.objects.filter(
                job=job,
                day_of_week=day_of_month.day_of_week,
                week_of_month=day_of_month.week_of_month,
            )
            num_assigned = len(now_assigned)
            if num_assigned > job.num_vols_required:
                job.num_vols_required = num_assigned
                job.save()


class LegacyPackerjobsubstitution(models.Model):
    date = models.DateField()
    packer_job = models.ForeignKey(LegacyPackerjob, models.DO_NOTHING)
    # who made the request
    requested_user = models.ForeignKey(
        LegacyUser, models.DO_NOTHING, blank=True, null=True)
    # person who fills
    volunteer = models.ForeignKey(LegacyVolunteer, models.DO_NOTHING)

    def _import(self):
        # getting job
        job_name = None
        if "hot" in self.packer_job.name.lower():
            job_name = PACKER_HOT
        elif "cold" in self.packer_job.name.lower():
            # using elif to be sure
            job_name = PACKER_COLD
        else:
            return "substitution for supervisor"

        job = Job.objects.get(name=job_name)

        # volunteer on the assignment
        if self.requested_user.username == LEGACY_OPENROUTE_USERNAME:
            assignment_volunteer = None
        else:
            assignment_volunteer = Volunteer.objects.get(
                user=User.objects.get(username=self.requested_user.username.lower())
            )
        if self.volunteer.user.username == LEGACY_OPENROUTE_USERNAME:
            substituting_volunteer = None
        else:
            substituting_volunteer = Volunteer.objects.get(
                user=User.objects.get(username=self.volunteer.user.username.lower())
            )

        day_of_month = date_to_day_of_month(self.date)
        assignments = Assignment.objects.filter(
            job=job,
            day_of_week=day_of_month.day_of_week,
            week_of_month=day_of_month.week_of_month,
            volunteer=assignment_volunteer,
        )
        assert assignments
        for ass in assignments:
            Substitution.objects.create(
                date=self.date,
                assignment=ass,
                volunteer=substituting_volunteer)


class LegacyPackerjobsubstitutionrequest(models.Model):
    date = models.DateField()
    created_by = models.ForeignKey(
        LegacyUser,
        models.DO_NOTHING,
        blank=True,
        null=True)
    packer_job = models.ForeignKey(LegacyPackerjob, models.DO_NOTHING)

    def _import(self):
        # getting job
        job_name = None
        if "hot" in self.packer_job.name.lower():
            job_name = PACKER_HOT
        elif "cold" in self.packer_job.name.lower():
            # using elif to be sure
            job_name = PACKER_COLD
        else:
            return "substitution for supervisor"

        job = Job.objects.get(name=job_name)

        # volunteer on the assignment
        if self.created_by.username == LEGACY_OPENROUTE_USERNAME:
            assignment_volunteer = None
        else:
            assignment_volunteer = Volunteer.objects.get(
                user=User.objects.get(username=self.created_by.username.lower())
            )

        day_of_month = date_to_day_of_month(self.date)
        assignments = Assignment.objects.filter(
            job=job,
            day_of_week=day_of_month.day_of_week,
            week_of_month=day_of_month.week_of_month,
            volunteer=assignment_volunteer,
        )
        assert assignments
        for ass in assignments:
            Substitution.objects.create(
                date=self.date, assignment=ass, volunteer=None)


class LegacyShuttleroute(models.Model):
    name = models.CharField(max_length=100)

    def _import(self):
        Job.objects.create(
            name=self.name,
            num_vols_required=1,
            job_type=JobType.objects.get_or_create(name=SHUTTLE_TYPE_NAME)[0],
            # currently not setting the recurrence, so it'll default to Mon -
            # Fri
        )


class LegacyVolunteershuttleroute(models.Model):
    """
    Recurrence to day_of_week week_of_month
    """

    recurrences = models.TextField()
    shuttle_route = models.ForeignKey(LegacyShuttleroute, models.DO_NOTHING)
    volunteer = models.ForeignKey(LegacyVolunteer, models.DO_NOTHING)

    def _import(self):
        # return f"{self.shuttle_route.name} recurs on {self.recurrences}"
        if self.volunteer.user.username == LEGACY_OPENROUTE_USERNAME:
            vol = None
        else:
            vol = Volunteer.objects.get(user=User.objects.get(
                username=self.volunteer.user.username.lower()))
        job = Job.objects.get(name=self.shuttle_route.name)
        for day_of_month in split_recurrence(self.recurrences):
            Assignment.objects.create(
                volunteer=vol,
                job=job,
                day_of_week=day_of_month.day_of_week,
                week_of_month=day_of_month.week_of_month,
            )


class LegacyShuttleroutesubstitution(models.Model):
    date = models.DateField()
    requested_user = models.ForeignKey(
        LegacyUser, models.DO_NOTHING, blank=True, null=True)
    shuttle_route = models.ForeignKey(LegacyShuttleroute, models.DO_NOTHING)
    volunteer = models.ForeignKey(LegacyVolunteer, models.DO_NOTHING)

    def _import(self):
        job = Job.objects.get(name=self.shuttle_route.name)

        if self.requested_user.username == LEGACY_OPENROUTE_USERNAME:
            assignment_volunteer = None
        else:
            assignment_volunteer = Volunteer.objects.get(
                user=User.objects.get(username=self.requested_user.username.lower())
            )
        if self.volunteer.user.username == LEGACY_OPENROUTE_USERNAME:
            substituting_volunteer = None
        else:
            substituting_volunteer = Volunteer.objects.get(
                user=User.objects.get(username=self.volunteer.user.username.lower())
            )

        day_in_month = date_to_day_of_month(self.date)

        assignment = Assignment.objects.get(
            job=job,
            day_of_week=day_in_month.day_of_week,
            week_of_month=day_in_month.week_of_month,
            volunteer=assignment_volunteer,
        )

        Substitution.objects.create(
            date=self.date,
            assignment=assignment,
            volunteer=substituting_volunteer)


class LegacyShuttleroutesubstitutionrequest(models.Model):
    date = models.DateField()
    created_by = models.ForeignKey(
        LegacyUser,
        models.DO_NOTHING,
        blank=True,
        null=True)
    shuttle_route = models.ForeignKey(LegacyShuttleroute, models.DO_NOTHING)

    def _import(self):
        # getting job
        job = Job.objects.get(name=self.shuttle_route.name)

        # volunteer on the assignment
        if self.created_by.username == LEGACY_OPENROUTE_USERNAME:
            assignment_volunteer = None
        else:
            assignment_volunteer = Volunteer.objects.get(
                user=User.objects.get(username=self.created_by.username.lower())
            )

        day_in_month = date_to_day_of_month(self.date)
        assignment = Assignment.objects.get(
            job=job,
            day_of_week=day_in_month.day_of_week,
            week_of_month=day_in_month.week_of_month,
            volunteer=assignment_volunteer,
        )
        Substitution.objects.create(
            date=self.date,
            assignment=assignment,
            volunteer=None)


class LegacyVolunteerroute(models.Model):
    """
    Need to split recurrence into many day_of_month
    """

    recurrences = models.TextField()
    route = models.ForeignKey(LegacyRoute, models.DO_NOTHING)
    volunteer = models.ForeignKey(LegacyVolunteer, models.DO_NOTHING)

    def _import(self):
        if self.volunteer.user.username == LEGACY_OPENROUTE_USERNAME:
            vol = None
        else:
            vol = Volunteer.objects.get(user=User.objects.get(
                username=self.volunteer.user.username.lower()))
        route = Route.objects.get(number=self.route.route)
        for day_of_month in split_recurrence(self.recurrences):
            Assignment.objects.create(
                volunteer=vol,
                job=route,
                day_of_week=day_of_month.day_of_week,
                week_of_month=day_of_month.week_of_month,
            )


class LegacySubstitution(models.Model):
    date = models.DateField()
    requested_user = models.ForeignKey(
        LegacyUser, models.DO_NOTHING, blank=True, null=True)
    route = models.ForeignKey(LegacyRoute, models.DO_NOTHING)
    volunteer = models.ForeignKey(LegacyVolunteer, models.DO_NOTHING)

    def _import(self):
        route = Route.objects.get(number=self.route.route)
        if self.requested_user.username == LEGACY_OPENROUTE_USERNAME:
            assigned_vol = None
        else:
            assigned_vol = Volunteer.objects.get(
                user=User.objects.get(
                    username=self.requested_user.username.lower()))
        day_of_month = date_to_day_of_month(self.date)
        try:
            assignment = Assignment.objects.get(
                job=route,
                volunteer=assigned_vol,
                day_of_week=day_of_month.day_of_week,
                week_of_month=day_of_month.week_of_month,
            )
        except Assignment.DoesNotExist:
            return f"{assigned_vol} is not working {route} on {day_of_month}, {self.date}"
        if self.volunteer.user.username == LEGACY_OPENROUTE_USERNAME:
            subing_vol = None
        else:
            subing_vol = Volunteer.objects.get(user=User.objects.get(
                username=self.volunteer.user.username.lower()))
        try:
            Substitution.objects.create(
                date=self.date, assignment=assignment, volunteer=subing_vol,
            )
        except IntegrityError as e:
            return f"{e}"


class LegacySubstitutionrequest(models.Model):
    date = models.DateField()
    created_by = models.ForeignKey(
        LegacyUser,
        models.DO_NOTHING,
        blank=True,
        null=True)
    route = models.ForeignKey(LegacyRoute, models.DO_NOTHING)

    def _import(self):
        route = Route.objects.get(number=self.route.route)
        if self.created_by.username == LEGACY_OPENROUTE_USERNAME:
            assigned_vol = None
        else:
            assigned_vol = Volunteer.objects.get(
                user=User.objects.get(
                    username=self.created_by.username.lower()))
        day_of_month = date_to_day_of_month(self.date)
        try:
            assignment = Assignment.objects.get(
                job=route,
                volunteer=assigned_vol,
                day_of_week=day_of_month.day_of_week,
                week_of_month=day_of_month.week_of_month,
            )
        except Assignment.DoesNotExist:
            return f"{assigned_vol} is not working {route} on {day_of_month}, {self.date}"
        Substitution.objects.create(
            date=self.date, assignment=assignment, volunteer=None,
        )
