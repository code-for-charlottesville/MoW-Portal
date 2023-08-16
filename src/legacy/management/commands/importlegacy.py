import traceback
from unittest.mock import patch

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Model

import legacy.models as legacy_models
from models.models import Customer, Route


class Command(BaseCommand):
    """
    READ THIS:
     - run with python3 manage.py importlegacy
     - to implement an import add an _import(self) method to the
        model you want to import
     - if there is an acceptable error, return the message from _import
         - the import will continue
     - if there is an unacceptable error, raise an Exception in _import
         - the import will be aborted, and all changes will be unrolled
    """

    help = "Import the Legacy* objects to the current models"

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-coordinates",
            action="store_true",
            default=False,
            help="Do not convert address into coordinates",
        )

    def handle(self, *args, **kwargs):
        self.stdout.write("Importing legacy models")
        no_coords = kwargs["no_coordinates"]
        try:
            if no_coords:
                with patch(
                    "interfaces.address_lookup.validate",
                    lambda *args, **kwargs: {"lat": None, "lng": None},
                ):
                    self.stdout.write("Not including coordinates")
                    self.run_imports()
            else:
                self.run_imports()
        except Exception:
            traceback.print_exc()
            self.stderr.write(
                self.style.ERROR("There was an error! ")
                + "To keep db consistent, all imports are unrolled."
            )

    def adjust_route_orders(self):
        """
        route ordering was not adjusted properly in legacy portal,
        this allows for the old data to be migrated to use
        order_with_respect_to Meta in django models
        """
        self.stdout.write("adjusting route orders")
        routes = Route.objects.all()
        for route in routes:
            route_number = route.number
            # get the legacy route
            legacy_route = legacy_models.LegacyRoute.objects.get(
                route=route_number)
            # get the legacy customers
            legacy_customers = legacy_models.LegacyCustomer.objects.filter(
                route=legacy_route
            ).order_by("route_order")

            # iterate over the customers
            new_customers = []
            for legacy_customer in legacy_customers:
                new_customer = Customer.objects.get(
                    first_name=legacy_customer.first_name,
                    last_name=legacy_customer.last_name,
                    contact=legacy_customer.contact,
                    contact_phone=legacy_customer.contact_phone,
                )
                new_customers.append(new_customer)
            route.set_customer_order([c.pk for c in new_customers])
        self.stdout.write(self.style.SUCCESS("Done adjusting route orders"))

    def run_imports(self):
        num_models = 0
        num_objects = 0
        for name, model in legacy_models.__dict__.items():
            if not self.should_import(model, name):
                continue
            self.stdout.write(f"Importing {name}")
            for x in model.objects.all():
                error = x._import()
                if error and len(error):
                    self.stderr.write(self.style.ERROR(error))
                else:
                    num_objects += 1
            num_models += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Finished importing {num_objects} objects from {num_models} models"
            )
        )
        self.adjust_route_orders()

    def should_import(self, instance, name):
        if not isinstance(instance, type):
            return False
        if not issubclass(instance, Model):
            return False
        if not name.startswith("Legacy"):
            return False
        if not hasattr(instance, "_import"):
            self.stdout.write(
                self.style.WARNING(f"Skipping {name}") +
                ", _import() not defined")
            return False
        return True
