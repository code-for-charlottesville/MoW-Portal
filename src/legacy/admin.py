from django.contrib import admin
from django.contrib.auth.models import User
from django.db import models

from . import models as my_models

# Register your models here.

for key, val in my_models.__dict__.items():
    if (
        isinstance(val, type)
        and issubclass(val, models.Model)
        and val is not User
        and not val._meta.abstract
        and key.startswith("Legacy")
    ):
        admin.site.register(val)
