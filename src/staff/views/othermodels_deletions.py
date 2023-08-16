"""Payments, Pets, PetFoods, Diets"""

from logging import getLogger

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render, reverse

from models.models import Diet, Payment, Pet, PetFood, DateRange

log = getLogger(__name__)

# TODO: fix these
# Foreign keys in the customer model cause a Protected Error
# when the delete button is pressed.


@staff_member_required
def delete_payment(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    payment.delete()
    return HttpResponseRedirect(reverse("staff:manage_payments"))


@staff_member_required
def delete_pet(request, pk):
    pet = get_object_or_404(Pet, pk=pk)
    pet.delete()
    return HttpResponseRedirect(reverse("staff:manage_pets"))


@staff_member_required
def delete_diet(request, pk):
    diet = get_object_or_404(Diet, pk=pk)
    diet.delete()
    return HttpResponseRedirect(reverse("staff:manage_diets"))


@staff_member_required
def delete_daterange(request, pk):
    dr = get_object_or_404(DateRange, pk=pk)
    dr.delete()
    return HttpResponseRedirect(reverse("staff:manage_dateranges"))


@staff_member_required
def delete_petfood(request, pk):
    pf = get_object_or_404(PetFood, pk=pk)
    pf.delete()
    return HttpResponseRedirect(reverse("staff:manage_petfoods"))
