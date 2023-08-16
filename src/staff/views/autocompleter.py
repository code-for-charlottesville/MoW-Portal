from dal import autocomplete
from django.db.models import Q

from interfaces.recurrence import days_of_week, weeks_of_month
from models.models import Assignment, Customer, Volunteer


class VolunteerAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):

        # Make sure the Volunteer User has a first name or last name listed
        qs = Volunteer.objects.all().exclude((Q(user__first_name='') & Q(user__last_name='')) |
                                             (Q(user__first_name=None) & Q(user__last_name=None)))

        if self.q:
            words = self.q.split()
            for word in words:
                qs = qs.filter(Q(user__first_name__icontains=word)
                               | Q(user__last_name__icontains=word))

        # Don't forget to filter out results depending on the visitor !

        return qs


class AssignmentAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !

        qs = Assignment.objects.all()

        if self.q:
            words = self.q.split()
            for word in words:
                query = (
                    Q(volunteer__user__first_name__icontains=word)
                    | Q(volunteer__user__last_name__icontains=word)
                    | Q(job__name__icontains=word)
                )
                if word in days_of_week:
                    query |= Q(day_of_week=days_of_week.index(word))
                if word in weeks_of_month:
                    query |= Q(week_of_month=weeks_of_month.index(word))
                qs = qs.filter(query)

        return qs


class CustomerAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !

        qs = Customer.objects.all()

        if self.q:
            words = self.q.split()
            for word in words:
                qs = qs.filter(Q(first_name__icontains=word)
                               | Q(last_name__icontains=word))

        return qs
