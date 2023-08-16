from datetime import date, timedelta
from logging import getLogger

from django.http import HttpResponseBadRequest, JsonResponse

from interfaces.recurrence import is_friday, is_weekend
from meals.constants import RETENTION
from models.models import (
    Actual,
    Assignment,
    Customer,
    CustomerRecord,
    DateRange,
    ManagerAnnouncement,
    Substitution,
    VolunteerRecord,
)

log = getLogger(__name__)


def write_customer_record():
    """
    This is a cron job that runs everyday to write the current customer/meal to CustomerRecord
    This ensures historical accuracy even when the Customer objects change over time
    """

    today = date.today()

    customers = Customer.objects.filter(active=1)

    for customer in customers:
        num_meals = customer.num_meals_on_day(today)
        if num_meals != 0:
            _, created = CustomerRecord.objects.update_or_create(
                customer=customer,
                date=today,
                defaults=dict(
                    num_meals=num_meals,
                    payment_type=customer.pays,
                    route_assigned=customer.route,
                ),
            )
            if created:
                log.info(f"Created CustomerRecord for {customer}")
        else:
            try:
                record = CustomerRecord.objects.get(
                    customer=customer, date=today,)
                record.delete()
                log.info(
                    f"Customer {customer} was recieving a meal, but now is not")
            except CustomerRecord.DoesNotExist:
                continue


def write_volunteer_record():
    """
    This is a cron job that runs everyday to write the current volunteer/job to VolunteerRecord
    This ensures historical accuracy even when the Volunteer objects change over time
    """
    today = date.today()
    actuals = set(Assignment.actuals(today, exclude_unfilled=True))
    existing = set()
    for record in VolunteerRecord.objects.filter(date=today):
        existing.add(
            Actual(
                volunteer=record.volunteer,
                job=record.job,
                date=today,
                original=record.original,
                is_substitution=record.is_substitution,
            )
        )
    to_add = actuals - existing
    to_delete = existing - actuals
    for actual in to_delete:
        record = VolunteerRecord.objects.get(**actual._asdict())
        record.delete()
        log.info(f"VolunteerRecord {record} deleted")
    for actual in to_add:
        record = VolunteerRecord.objects.create(**actual._asdict())
        log.info(f"VolunteerRecord {record} created")


def delete_old_customer_record():
    custs = CustomerRecord.objects.filter(
        date__lt=date.today() - timedelta(days=RETENTION))
    for cust in custs:
        cust.delete()
        log.info(f"Deleting {cust}")


def delete_old_volunteer_record():
    vols = VolunteerRecord.objects.filter(
        date__lt=date.today() - timedelta(days=RETENTION))
    for vol in vols:
        log.info(f"Deleting {vol}")
        vol.delete()


def delete_old_substitutions():
    subs = Substitution.objects.filter(
        date__lt=date.today() - timedelta(days=RETENTION))
    for sub in subs:
        log.info(f"Deleting {sub}")
        sub.delete()


def delete_old_daterange():
    drs = DateRange.objects.filter(
        start_date__lt=date.today() - timedelta(days=RETENTION),
        end_date__lt=date.today() - timedelta(days=RETENTION),
    )
    for dr in drs:
        log.info(f"Deleting {dr}")
        dr.delete()


def delete_old_announcement():
    announces = ManagerAnnouncement.objects.filter(
        display_until__lt=date.today() - timedelta(days=RETENTION)
    )
    for a in announces:
        log.info(f"Deleting {a}")
        a.delete()


def daily_cron(request):
    write_customer_record()
    write_volunteer_record()
    delete_old_customer_record()
    delete_old_volunteer_record()
    delete_old_substitutions()
    delete_old_daterange()
    delete_old_announcement()
    log.info("daily cron successful")
    return JsonResponse({"status": "ok"})
