import datetime
import json
import time

from google.cloud import storage
from requests.models import HTTPError

from cron import four11

PARSEABLE_PERIODS = ["A", "B", "C", "D", "E", "F", "G", "H"]
FREE_PERIOD_CLASS = {
    "room": None,
    "name": "Free Period",
    "teacher": None,
    "teacher_username": None,
    "department": None,
}
MAX_ERRORS = 10


# Return the year of the current graduating class
# I.E. the 2019-2020 school year would return 2020
def get_current_school_year():
    now = datetime.datetime.now()
    end_year = now.year
    if now.month >= 7 or (now.month >= 6 and now.day >= 10):
        # Old school year has ended, add one to year
        end_year += 1
    return end_year


def add_free_periods_to_schedule(course_list):
    for period in PARSEABLE_PERIODS:
        contains = False
        for clss in course_list:
            if clss["period"] == period:
                contains = True
                break

        if not contains:
            course_list.append(FREE_PERIOD_CLASS.copy())
            course_list[-1]["period"] = period
    # Modifies course list in place


def decode_trimester_classes(four11_response):
    trimester_classes = []
    trimester = four11_response["sections"]
    for clss in trimester:
        if clss["period"] in PARSEABLE_PERIODS:
            obj = {
                "period": clss["period"],
                "room": clss["location"],
                "name": clss["course"],
                "teacher_username": clss["teacher"],
                "department": clss["department"],
            }
            trimester_classes.append(obj)

    add_free_periods_to_schedule(trimester_classes)
    trimester_classes.sort(key=lambda x: x["period"])
    return trimester_classes


def download_schedule(client, username, year):
    person = {"classes": []}

    # For each trimester
    for term_id in range(1, 4):
        briggs_person = client.get_courses(username, term_id)
        person["classes"].append(decode_trimester_classes(briggs_person))

    individual = briggs_person["individual"]
    person["sid"] = individual["id"]
    if individual.get("preferred_name"):
        person["preferred_name"] = individual["preferred_name"]
    person["firstname"] = individual["firstname"]
    person["lastname"] = individual["lastname"]
    person["gradyear"] = individual["gradyear"]
    # Recompute the username, don't just stuff the one we were passed
    person["username"] = individual["email"].split("@")[0]

    # Find advisor
    person["advisor"] = None
    for section in briggs_person["sections"]:
        if "advisory" in section["course"].lower():
            person["advisor"] = section["teacher"]

    # Convert grade to gradyear
    person["grade"] = None
    if person["gradyear"]:
        person["grade"] = 12 - (person["gradyear"] - year)

    return person


def download_schedule_with_retry(client, username, year):
    for i in range(3):
        try:
            return download_schedule(client, username, year)
        except (HTTPError, ValueError) as e:  # catches HTTP and JSON errors
            print(f"Error for {username}: {e}, retrying")
            if i != 2:
                time.sleep(1)
            else:
                raise e


def crawl_schedules(dry_run=False, verbose=False):
    print(f"Starting schedule crawl, dry_run={dry_run}")
    start = time.time()
    school_year = get_current_school_year()

    # Open the bucket
    storage_client = storage.Client()
    data_bucket = storage_client.bucket("epschedule-data")

    username_blob = data_bucket.blob("usernames.json")
    usernames = json.loads(username_blob.download_as_string())
    usernames.remove("dyezbick")

    schedules = {}
    errors = 0

    four11_client = four11.Four11Client()
    usernames = [u.username() for u in four11_client.get_people()]
    usernames.remove("dyezbick")

    for username in usernames:
        try:
            schedules[username] = download_schedule_with_retry(
                four11_client, username, school_year
            )
            if verbose:
                print(f"Crawled user {username}")
        except NameError:
            errors += 1
            print(f"Could not crawl user {username}")

    print(f"Schedule crawl completed, {len(schedules)} downloaded, {errors} errors")

    # First, do some sanity checks that all users are accounted for, that the number of
    # errors is reasonable, and that schedules have the right shape

    assert len(schedules) + errors == len(usernames)
    assert errors < MAX_ERRORS
    for username, schedule in schedules.items():
        assert len(schedule["classes"]) == 3
        for trimester in schedule["classes"]:
            assert len(trimester) == 8 or len(trimester) == 9
        assert bool(schedule["gradyear"]) == bool(schedule["grade"])

    print("Schedules passed sanity check")

    # Now do the upload, unless it's a dry run
    if not dry_run:
        schedule_blob = data_bucket.blob("schedules.json")
        schedule_blob.upload_from_string(json.dumps(schedules))
    print("Schedule crawl took {:.2f} seconds".format(time.time() - start))
