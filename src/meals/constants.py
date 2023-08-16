from datetime import datetime

RRULE_START = datetime(year=1970, month=1, day=1)
RRULE_COUNT = 31

RETENTION = 180

OPEN_ROUTE = "OPEN JOB"
OPEN_SUBSTITUTION = "Open Substitution Request"
UNASSIGNED_JOB = "No Assignment"

VOLS_PER_HOT = 3
VOLS_PER_COLD = 2

PACKER_HOT = "Packer Hot"
PACKER_COLD = "Packer Cold"

PACKER_TYPE_NAME = "Packer"
SHUTTLE_TYPE_NAME = "Shuttle"
ROUTE_TYPE_NAME = "Route"


REPORT_TYPES = [
    "substitutions-report",
    "job-overview-report",
    "customer-status-report",
    "client-birthday-report",
    "volunteer-birthday-report",
    "daily-count-report",
    "monthly-billing-report",
    "missing-feedback-report"
]

MOW_LAT = 38.037740
MOW_LON = -78.487490

# DELIVERY_STATUS = {
#     "AT_DOOR": "Left at door",
#     "ANSWERED": "Client answered"
# }

DELIVERY_STATUS = ["Left at door", "Client answered"]

CUSTOMER_STATUS = ['All good!', 'Needs follow up', "N/A"]
