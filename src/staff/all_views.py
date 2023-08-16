"""
combines all of the staff views for easy imports
"""

import staff.views.announcements
import staff.views.assignment_management
import staff.views.autocompleter
import staff.views.customer_management
import staff.views.email
import staff.views.index
import staff.views.job_management
import staff.views.othermodels_deletions
import staff.views.reports
import staff.views.substitution_management
import staff.views.volunteer_management

modules = [
    staff.views.announcements,
    staff.views.assignment_management,
    staff.views.customer_management,
    staff.views.index,
    staff.views.job_management,
    staff.views.reports,
    staff.views.substitution_management,
    staff.views.volunteer_management,
    staff.views.othermodels_deletions,
    staff.views.email,
    staff.views.autocompleter,
]

for module in modules:
    for key in dir(module):
        globals()[key] = getattr(module, key)
