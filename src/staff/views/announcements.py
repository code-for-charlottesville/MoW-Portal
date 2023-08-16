"""
Views file for creating and deleting announcements
"""

from logging import getLogger

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render

from models.models import ManagerAnnouncement
from staff.forms import AnnouncementForm

log = getLogger(__name__)


@staff_member_required
def create_announcement(request):
    """
    This displays the form to create an announcement that will be shown on the index page.
    """
    if request.method == "GET":
        form = AnnouncementForm()
        context = {"form": form}
        return render(request, "create_announcement.html", context)

    if request.method == "POST":
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("staff:index")


@staff_member_required
def delete_announcement(request, pk):
    """
    This removes an announcement from the database.
    """
    announcement = get_object_or_404(ManagerAnnouncement, pk=pk)
    announcement.delete()
    return redirect("staff:index")
