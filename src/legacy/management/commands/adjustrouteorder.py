import traceback
from unittest.mock import patch

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Model
from pprint import pprint
import legacy.models as legacy_models
from models.models import Customer, Route


class Command(BaseCommand):
    """
     - run with python3 manage.py adjustrouteorder
    """

    def handle(self, *args, **kwargs):
        """
        this allows for the old data to be migrated to use
        order_with_respect_to Meta in django models
        """
        log_dict = {}
        self.stdout.write("adjusting route orders")
        routes = Route.objects.all()
        for route in routes:
            route_number = route.number
            log_dict[f"Route {route_number}"] = {}
            self.stdout.write(f"route number: {route_number}")
            # get the legacy route
            legacy_route = legacy_models.LegacyRoute.objects.get(
                route=route_number)
            # get the legacy customers
            legacy_customers = legacy_models.LegacyCustomer.objects.filter(
                route=legacy_route
            ).order_by("route_order")
            # iterate over the customers
            legacy_customer_order = [
                f"{c.first_name} {c.last_name}" for c in legacy_customers]
            current_customer_order = [
                f"{c.first_name} {c.last_name}, ORDER: {c._order}" for c in Customer.objects.filter(
                    route=Route.objects.get(
                        number=route_number)).order_by('_order')]
            added_to_route_after_legacy_dump = []
            for person in current_customer_order:
                if person not in legacy_customer_order:
                    added_to_route_after_legacy_dump.append(person)
            taken_off_route_after_legacy_dump = []
            for person in legacy_customer_order:
                if person not in current_customer_order:
                    taken_off_route_after_legacy_dump.append(person)
            log_dict[f"Route {route_number}"] = {
                'added_to_route_after_legacy_dump': added_to_route_after_legacy_dump,
                'taken_off_route_after_legacy_dump': taken_off_route_after_legacy_dump}
            self.stdout.write(
                f"legacy customer order: {legacy_customer_order}")
            self.stdout.write(
                f"current customer order: {current_customer_order}")
            res = input("Would you like to adjust? y/n: ")
            if res == "y":
                try:
                    self.stdout.write("adjusting...")
                    new_customers = []
                    for legacy_customer in legacy_customers:
                        print(
                            f"Customer: {legacy_customer.first_name} {legacy_customer.last_name}")
                        new_customer = Customer.objects.get(
                            first_name=legacy_customer.first_name,
                            last_name=legacy_customer.last_name
                        )
                        new_customers.append(new_customer)
                    route.set_customer_order([c.pk for c in new_customers])
                    # clean _order column
                    current_customers = Customer.objects.filter(route=route)
                    route.set_customer_order([c.pk for c in current_customers])
                    current_customer_order = [
                        f"{c.first_name} {c.last_name}, ORDER: {c._order}" for c in Customer.objects.filter(
                            route=Route.objects.get(
                                number=route_number)).order_by('_order')]
                    print(
                        f"Order after adjustment:\n {current_customer_order}")
                except Customer.DoesNotExist:
                    print("SKIPPING THIS ROUTE--COULDN'T FIND CUSTOMER")
        self.stdout.write(self.style.SUCCESS("Done adjusting route orders"))
