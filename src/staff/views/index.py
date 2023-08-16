"""
Views file for staff index page
"""

import datetime
from logging import getLogger

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

from models.models import ManagerAnnouncement, Substitution

log = getLogger(__name__)


def query_substitutions_table(number_of_days, vol):
    """
    :param number_of_days: number of days in advance
    :return: Substitution queryset
    queries the substitutions table for the substitutions
    from today's date until however many days are passed in
    """
    startdate = datetime.date.today()
    # Change the timedelta to look for the number of weeks in advance
    enddate = startdate + datetime.timedelta(days=number_of_days - 1)
    sub_query = Substitution.objects.filter(date__range=[startdate, enddate])
    sub_day_dict = {}  # will be date string:subs for that day.
    for i in range(number_of_days):
        search_day = datetime.date.today() + datetime.timedelta(days=i)
        # lets skip weekends for now
        day_of_week = search_day.isoweekday()
        if day_of_week == 6 or day_of_week == 7:
            continue
        sub_day_query = sub_query.filter(date=search_day, volunteer=vol)
        sub_day_dict[search_day.strftime("%A, %B %d")] = sub_day_query

    return sub_day_dict


@staff_member_required
def index(request):
    """
    Welcome page
    """
    alert_query = ManagerAnnouncement.objects.filter(
        display_until__gte=datetime.date.today())
    sub_day_dict = query_substitutions_table(7, None)
    return render(request, "welcome-staff.html",
                  {"subs": sub_day_dict, "alerts": alert_query})
