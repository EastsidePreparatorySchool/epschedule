import copy
import datetime
import json
import os
import re
import time

import google.oauth2.id_token
from flask import Flask, abort, make_response, render_template, request, session
from google.auth.transport import requests
from google.cloud import datastore, secretmanager, storage

from cron.photos import crawl_photos, hash_username
from cron.schedules import crawl_schedules
from cron.update_lunch import get_lunches_since_date, read_lunches

app = Flask(__name__)

verify_firebase_token = None
datastore_client = None
SCHEDULE_INFO = None
DAYS = None
TERM_STARTS = []


def init_app(test_config=None):
    """Initialize the app and set up global variables."""
    global verify_firebase_token
    global datastore_client
    global SCHEDULE_INFO
    global DAYS
    global TERM_STARTS
    app.permanent_session_lifetime = datetime.timedelta(days=3650)
    if test_config is None:
        # Authenticate ourselves
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service_account.json"

        # Get application secret key
        secret_client = secretmanager.SecretManagerServiceClient()
        app.secret_key = secret_client.access_secret_version(
            request={"name": "projects/epschedule-v2/secrets/session_key/versions/1"}
        ).payload.data

        verify_firebase_token = (
            lambda token: google.oauth2.id_token.verify_firebase_token(
                token, requests.Request()
            )
        )

        storage_client = storage.Client()
        data_bucket = storage_client.bucket("epschedule-data")
        SCHEDULE_INFO = json.loads(
            data_bucket.blob("schedules.json").download_as_string()
        )
        DAYS = json.loads(data_bucket.blob("master_schedule.json").download_as_string())

        datastore_client = datastore.Client()
    else:
        app.config.from_mapping(test_config)

        def verify_firebase_token(token):
            return json.loads(token)

        datastore_client = app.config["DATASTORE"]
        SCHEDULE_INFO = app.config["SCHEDULES"]
        DAYS = app.config["MASTER_SCHEDULE"]
    TERM_STARTS = get_term_starts(DAYS[0])


def get_term_starts(days):
    """Return a list of datetime objects for the start of each trimester."""
    return [
        find_day(days, ".*"),
        find_day(days, ".*End.*Fall Term") + datetime.timedelta(days=1),
        find_day(days, ".*End.*Winter Term") + datetime.timedelta(days=1),
    ]


def find_day(days, regex):
    """Find the first day that matches the given regex"""
    for day in days:
        if re.match(regex, days[day]):
            return datetime.datetime.strptime(day, "%Y-%m-%d").date()
    assert False, f"No day matched {regex}"


def get_term_id():
    """Return the current trimester index (fall=0, winter=1, spring=2)"""
    now = datetime.datetime.now()
    for i in range(len(TERM_STARTS) - 1):
        if now < TERM_STARTS[i + 1]:
            return i
    return 2


def username_to_email(username):
    return username + "@eastsideprep.org"


def is_teacher_schedule(schedule):
    return not schedule["grade"]


def get_schedule_data():
    return SCHEDULE_INFO


def get_schedule(username):
    schedules = get_schedule_data()
    if username not in schedules:
        return None
    return schedules[username]


def gen_photo_url(username, icon=False):
    return "https://epschedule-avatars.storage.googleapis.com/{}".format(
        hash_username(app.secret_key, username, icon)
    )


def gen_login_response():
    template = make_response(render_template("login.html"))
    # Clear all cookies
    session.pop("username", None)
    template.set_cookie("token", "", expires=0)
    return template


def get_user_key(username):
    return datastore_client.key("user", username)


def get_database_entry(username):
    return datastore_client.get(get_user_key(username))


def get_database_entries(usernames):
    keys = [get_user_key(x) for x in usernames]
    return datastore_client.get_multi(keys)


@app.route("/")
def main():
    # Tokens are used during login, but after that we use our own system
    # If they have a token, we should always eat it and give them either
    # a proper auth cookie or the login page

    token = request.cookies.get("token")
    if token:
        try:
            claims = verify_firebase_token(token)
            session.permanent = True
            session["username"] = claims["email"].split("@")[0]

            # Make them a privacy object if it doesn't exist
            key = get_user_key(session["username"])
            if not datastore_client.get(key):
                user = datastore.Entity(key=key)
                user.update(
                    {
                        "joined": datetime.datetime.utcnow(),
                        "share_photo": True,
                        "share_schedule": True,
                    }
                )
                datastore_client.put(user)

        except ValueError:
            return gen_login_response()

    elif "username" not in session:
        return gen_login_response()

    # Handler for how to serialize date objs into json
    response = make_response(
        render_template(
            "index.html",
            schedule=json.dumps(get_schedule(session["username"])),
            days=json.dumps(DAYS),
            components="static/components.html",
            # gets the last 28 days of lunches
            lunches=get_lunches_since_date(
                datetime.date.today() - datetime.timedelta(28)
            ),
            # gets the trimester starts in a format JS can parse
            term_starts=json.dumps([d.isoformat() for d in TERM_STARTS]),
        )
    )
    response.set_cookie("token", "", expires=0)
    return response


@app.route("/class/<period>")
def handle_class(period):
    if "username" not in session:
        abort(403)

    schedule = get_schedule(session["username"])
    term = int(request.args.get("term_id"))

    class_name = next(
        (c for c in schedule["classes"][term] if c["period"].lower() == period)
    )

    censor = not is_teacher_schedule(schedule)
    class_schedule = get_class_schedule(class_name, term, censor=censor)
    return json.dumps(class_schedule)


# Functions to generate and censor class schedules

# List of people who opted out of photo sharing
def gen_opted_out_table():
    # TODO write this
    return set()


def is_same_class(a, b):
    return a["teacher_username"] == b["teacher_username"] and a["period"] == b["period"]


def get_class_schedule(user_class, term_id, censor=True):
    result = {
        "period": user_class["period"],
        "teacher": user_class["teacher_username"],
        "term_id": term_id,
        "students": [],
    }

    opted_out = set()

    for schedule in get_schedule_data().values():
        for classobj in schedule["classes"][term_id]:
            if is_same_class(user_class, classobj):
                # We only include teacher schedules in free periods
                if (not is_teacher_schedule(schedule)) or classobj[
                    "name"
                ] == "Free Period":
                    student = {
                        "firstname": get_first_name(schedule),
                        "lastname": schedule["lastname"],
                        "grade": schedule["grade"],
                        "username": schedule["username"],
                        "email": username_to_email(schedule["username"]),
                        "photo_url": gen_photo_url(schedule["username"], True),
                    }
                    result["students"].append(student)

    # Sorts alphabetically, then sorts teachers from students
    result["students"] = sorted(
        sorted(result["students"], key=lambda s: s["firstname"]),
        key=lambda s: str(s["grade"]),
    )

    # Censor photos
    if censor:
        privacy_settings = get_database_entries(
            [x["username"] for x in result["students"]]
        )
        opted_out = [x.key.name for x in privacy_settings if not x.get("share_photo")]
        for student in result["students"]:
            if student["username"] in opted_out:
                student["photo_url"] = "/static/images/placeholder_small.png"

    return result


# TODO rename this to /user since it's for students and teachers
@app.route("/student/<target_user>")
def handle_user(target_user):
    if "username" not in session:
        abort(403)

    # TODO finish privacy logic
    user_schedule = get_schedule(session["username"])
    target_schedule = get_schedule(target_user)

    priv_settings = {"share_photo": True, "share_schedule": True}
    # Teachers don't see and can't set privacy settings
    if (not is_teacher_schedule(user_schedule)) and (
        not is_teacher_schedule(target_schedule)
    ):
        priv_obj = get_database_entry(target_user)
        if priv_obj:
            priv_settings = dict(priv_obj.items())

    if not priv_settings["share_schedule"]:
        target_schedule = sanitize_schedule(target_schedule, user_schedule)

    # Generate email address
    target_schedule["email"] = username_to_email(target_user)

    if priv_settings["share_photo"]:
        target_schedule["photo_url"] = gen_photo_url(target_user, False)
    else:
        target_schedule["photo_url"] = "/static/images/placeholder.png"

    return json.dumps(target_schedule)


def sanitize_schedule(orig_schedule, user_schedule):
    schedule = copy.deepcopy(orig_schedule)
    for i in range(0, len(schedule["classes"])):
        for k in range(0, len(schedule["classes"][i])):
            # If the class is not shared
            if not schedule["classes"][i][k] in user_schedule["classes"][i]:
                schedule["classes"][i][k] = sanitize_class(schedule["classes"][i][k])

    return schedule


def sanitize_class(orig_class_obj):
    class_obj = orig_class_obj.copy()
    study_halls = ["Study Hall", "GSH", "Free Period"]

    if class_obj["name"] in study_halls:
        class_obj["name"] = "Free Period"
    else:
        class_obj["name"] = "Hidden"

    class_obj["teacher"] = ""
    class_obj["room"] = ""

    return class_obj  # Return the class object


@app.route("/period/<period>")
def handle_period(period):
    if "username" not in session:
        abort(403)

    # TODO read this as a URL parameter
    term = get_term_id()
    schedule = get_schedule(session["username"])
    grade_range = get_grade_range(schedule["grade"])
    available = get_available(period, term, grade_range)
    current_class = pop_current_class(available, schedule, term, period)

    return json.dumps(
        {
            "period": period.upper(),
            "term_id": term,
            "freerooms": get_free_rooms(period, term),
            "classes": [available] * 3,  # TODO add support for other terms
            "currentclass": current_class,
            "altperiods": None,  # TODO add this in UI
        }
    )


# Functions to generate period information


def get_free_rooms(period, term):
    free = set()
    occupied = set()
    for schedule in get_schedule_data().values():
        if is_teacher_schedule(schedule):
            continue
        for clss in schedule["classes"][term]:
            if clss["period"] == period.upper():
                occupied.add(clss["room"])
            else:
                free.add(clss["room"])
    return list(free - occupied)


def get_grade_range(grade):
    if not grade:
        return None
    elif grade <= 8:  # Middle school
        return range(5, 9)
    else:
        return range(9, 13)


def get_available(period, term, grades):
    # We index available by teacher username, since
    # two of the same class could happen at once
    available = {}
    for schedule in get_schedule_data().values():
        c = get_class_by_period(schedule["classes"][term], period)
        key = c["teacher_username"]
        if not key:  # Skip free periods
            continue
        if key in available and not is_teacher_schedule(schedule):
            available[key]["students"] += 1
        elif schedule["grade"] in grades:
            available[key] = copy.copy(c)
            available[key]["students"] = 1
    return list(available.values())


# Modifies 'available' in place by removing and returning
# the desired item
def pop_current_class(available, schedule, term, period):
    current_class = get_class_by_period(schedule["classes"][term], period)
    for c in available:
        if c["teacher_username"] == current_class["teacher_username"]:
            available.remove(c)
            return c


def get_class_by_period(schedule, period):
    for c in schedule:
        if c["period"].lower() == period.lower():
            return c


# Change and view privacy settings
@app.route("/privacy", methods=["GET", "POST"])
def handle_settings():
    if "username" not in session:
        abort(403)
    user = get_database_entry(session["username"])

    if request.method == "GET":
        user_privacy_dict_raw = dict(user.items())
        user_privacy_dict = {
            "share_photo": user_privacy_dict_raw["share_photo"],
            "share_schedule": user_privacy_dict_raw["share_schedule"],
        }
        return json.dumps(user_privacy_dict)

    elif request.method == "POST":
        user.update(
            {
                "share_photo": request.form["share_photo"] == "true",
                "share_schedule": request.form["share_schedule"] == "true",
            }
        )
        datastore_client.put(user)
        return json.dumps({})


@app.route("/search/<keyword>")
def handle_search(keyword):
    if "username" not in session:
        abort(403)

    results = []
    for schedule in get_schedule_data().values():
        test_keyword = get_first_name(schedule) + " " + schedule["lastname"]
        if keyword.lower() in test_keyword.lower():
            results.append({"name": test_keyword, "username": schedule["username"]})
            if len(results) >= 5:  # We only display five results
                break
    return json.dumps(results)


def get_first_name(schedule):
    return schedule.get("preferred_name") or schedule["firstname"]


# This is a post because it changes things
@app.route("/logout", methods=["POST"])
def handle_sign_out():
    session.clear()
    return json.dumps({})


# Cron tasks
@app.route("/cron/schedules")
def handle_cron_schedules():
    crawl_schedules()
    return "OK"


@app.route("/cron/photos")
def handle_cron_photos():
    crawl_photos()
    return "OK"


@app.route("/cron/update_lunch")
def handle_cron_lunches():
    read_lunches()
    return "OK"
