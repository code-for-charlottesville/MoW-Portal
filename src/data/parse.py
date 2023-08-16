import json
from collections import Counter
from datetime import datetime, timedelta
from pprint import pprint

all_models = {
    "mailer.messagelog",
    "reports.reportday",
    "axes.accesslog",
    "sessions.session",
    "admin.logentry",
    "auth.user",
    "customers.customer",
    "users.volunteer",
    "mailer.message",
    "users.volunteerroute",
    "axes.accessattempt",
    "users.substitutionrequest",
    "routes.route",
    "users.volunteerpackerjob",
    "customers.diet",
    "customers.pet",
    "users.substitution",
    "users.packerjobsubstitutionrequest",
    "users.volunteershuttleroute",
    "customers.petfood",
    "customers.payment",
    "users.shuttleroutesubstitution",
    "users.packerjobsubstitution",
    "customers.daterange",
    "users.shuttleroute",
    "users.packerjob",
    "users.shuttleroutesubstitutionrequest",
    "sites.site",
}


delete_apps = {
    "sessions",
    "axes",
    "mailer",
    "admin",
    "sites",
}

delete_fields = {
    "groups",
    "user_permissions",
}

rename_apps_to = "legacy.Legacy"

report_day_retention = 181

_cutoff = datetime.now() - timedelta(days=report_day_retention)


def delete_perms_and_groups(record):
    """ Returns and mutates! """
    for field in delete_fields:
        if field in record["fields"]:
            del record["fields"][field]
    return record


def rename(record):
    """ Returns and mutates! """
    model = record["model"]
    record["model"] = f"{rename_apps_to}{model[model.index('.')+1:]}"
    return record


def is_recent(record):
    if not record["model"] == "reports.reportday":
        return True
    dt = datetime.strptime(record["fields"]["date"], "%Y-%m-%d")
    return dt > _cutoff


def is_important(record):
    return record["model"].split(".")[0] not in delete_apps


with open("db.json") as file:
    data = json.load(file)
    print(f"Total db length: {len(data)}")
    models = Counter(x["model"] for x in data)
    pprint(models)

    new_data = list(
        map(
            delete_perms_and_groups,
            map(rename, filter(is_recent, filter(is_important, data,),),),
        ),
    )
    with open("legacy_db.json", "w") as output:
        json.dump(new_data, output)
