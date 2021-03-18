import copy
import datetime
import json
import os
import time

from flask import Flask, abort, render_template, request, session, make_response
from google.auth.transport import requests
from google.cloud import datastore, storage, secretmanager
import google.oauth2.id_token

from cron.photos import hash_username

app = Flask(__name__)

verify_firebase_token = None
datastore_client = None
SCHEDULE_INFO = None
DAYS = None
FALL_TRI_END = datetime.datetime(2020, 11, 23, 15, 30, 0, 0)
WINT_TRI_END = datetime.datetime(2021, 3, 6, 15, 30, 0, 0)

def init_app(test_config=None):
    global verify_firebase_token
    global datastore_client
    global SCHEDULE_INFO
    global DAYS
    app.permanent_session_lifetime = datetime.timedelta(days=3650)
    if test_config is None:
        # Authenticate ourselves
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service_account.json"

        # Get application secret key
        secret_client = secretmanager.SecretManagerServiceClient()
        app.secret_key = secret_client.access_secret_version(request={
            "name": "projects/epschedule-v2/secrets/session_key/versions/1"
        }).payload.data

        verify_firebase_token = lambda token: \
            google.oauth2.id_token.verify_firebase_token(
                token, requests.Request())

        storage_client = storage.Client()
        data_bucket = storage_client.bucket("epschedule-data")
        SCHEDULE_INFO = json.loads(
            data_bucket.blob("schedules.json").download_as_string())
        DAYS = json.loads(
            data_bucket.blob("master_schedule.json").download_as_string())

        datastore_client = datastore.Client()
    else:
        app.config.from_mapping(test_config)
        verify_firebase_token = lambda token: json.loads(token)
        datastore_client = app.config['DATASTORE']
        SCHEDULE_INFO = app.config['SCHEDULES']
        DAYS = app.config['MASTER_SCHEDULE']

def username_to_email(username):
    return username + "@eastsideprep.org"

def is_teacher_schedule(schedule):
    return not schedule["grade"]

def get_term_id():
    now = datetime.datetime.now()
    if now < FALL_TRI_END:
        default = 0
    elif now < WINT_TRI_END:
        default = 1
    else:
        default = 2
    return request.form.get('input_name', default)

def get_schedule_data():
    return SCHEDULE_INFO

def gen_photo_url(username, icon=False):
    return "https://epschedule-avatars.storage.googleapis.com/{}".format(
        hash_username(app.secret_key, username, icon))

def gen_login_response():
    template = make_response(
        render_template("login.html", components="static/components.html"))
    # Clear all cookies
    session.pop('username', None)
    template.set_cookie('token', '', expires=0)
    return template

def get_schedule(username):
    schedules = get_schedule_data()
    if username in schedules:
        return schedules[username]
    else:
        return None

def get_user_key(username):
    return datastore_client.key('user', username)

def get_database_entry(username):
    return datastore_client.get(get_user_key(username))

def get_database_entries(usernames):
    keys = [get_user_key(x) for x in usernames]
    return datastore_client.get_multi(keys)

@app.route('/')
def main():
    # Tokens are used during login, but after that we use our own system
    # If they have a token, we should always eat it and give them either
    # a proper auth cookie or the login page

    token = request.cookies.get("token")
    if token:
        try:
            claims = verify_firebase_token(token)
            session.permanent = True
            session['username'] = claims['email'].split("@")[0]

            # Make them a privacy object if it doesn't exist
            key = get_user_key(session['username'])
            if not datastore_client.get(key):
                user = datastore.Entity(key=key)
                user.update({
                    'joined': datetime.datetime.utcnow(),
                    'share_photo': True,
                    'share_schedule': True
                })
                datastore_client.put(user)

        except ValueError as exc:
            return gen_login_response()

    elif 'username' not in session:
        return gen_login_response()

    # Handler for how to serialize date objs into json
    response = make_response(render_template("index.html",
        schedule = json.dumps(get_schedule(session['username'])),
        days = json.dumps(DAYS),
        components = "static/components.html",
        lunches = "[]",
        fall_end_unix = str(int(time.mktime(FALL_TRI_END.timetuple())) * 1000),
        wint_end_unix = str(int(time.mktime(WINT_TRI_END.timetuple())) * 1000)
    ))
    response.set_cookie('token', '', expires=0)
    return response

@app.route('/class/<period>')
def handle_class(period):
    if 'username' not in session:
        abort(403)

    schedule = get_schedule(session['username'])
    term = int(request.args.get('term_id'))

    class_name = next(
        (
            c for c in schedule["classes"][term]
            if c["period"].lower() == period
        )
    )

    censor = not is_teacher_schedule(schedule)
    class_schedule = get_class_schedule(class_name, term, censor=censor)
    return json.dumps(class_schedule)

### Functions to generate and censor class schedules

# List of people who opted out of photo sharing
def gen_opted_out_table():
    # TODO write this
    return set()

def is_same_class(a, b):
    return (
        a["teacher_username"] == b["teacher_username"]
        and a["period"] == b["period"]
    )

def get_class_schedule(user_class, term_id, censor=True):
    #print(user_class)
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
                #print("Found same class")
                #print(schedule)
                #print(is_teacher_schedule(schedule))
                # We only include teacher schedules in free periods
                if (not is_teacher_schedule(schedule)) or classobj["name"] == "Free Period":
                    #print("Appending")
                    student = {
                        "firstname": schedule["firstname"],
                        "lastname": schedule["lastname"],
                        "grade": schedule["grade"],
                        "username": schedule["username"],
                        "email": username_to_email(schedule["username"]),
                        "photo_url": gen_photo_url(schedule["username"], True),
                    }
                    result["students"].append(student)

    # Sorts alphabetically, then sorts teachers from students
    result["students"] = sorted(
        sorted(result["students"], key = lambda s: s["firstname"]),
        key = lambda s: str(s["grade"]))

    # Censor photos
    if censor:
        privacy_settings = get_database_entries([x["username"] for x in result["students"]])
        opted_out = [x.key.name for x in privacy_settings if not x.get("share_photo")]
        for student in result["students"]:
            if student["username"] in opted_out:
                student["photo_url"] = "/static/images/placeholder_small.png"

    return result


# TODO rename this to /user since it's for students and teachers
@app.route('/student/<target_user>')
def handle_user(target_user):
    if 'username' not in session:
        abort(403)

    # TODO finish privacy logic
    user_schedule = get_schedule(session['username'])
    target_schedule = get_schedule(target_user)

    priv_settings = {"share_photo": True, "share_schedule": True}
    # Teachers don't see and can't set privacy settings
    if ((not is_teacher_schedule(user_schedule)) and
        (not is_teacher_schedule(target_schedule))):
        priv_obj = get_database_entry(target_user)
        if priv_obj:
            priv_settings = dict(priv_obj.items())
            #print(priv_settings)

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

@app.route('/period/<period>')
def handle_period(period):
    if 'username' not in session:
        abort(403)

    # TODO read this as a URL parameter
    term = get_term_id()
    schedule = get_schedule(session['username'])
    grade_range = get_grade_range(schedule["grade"])
    available = get_available(period, term, grade_range)
    current_class = pop_current_class(available, schedule, term, period)

    return json.dumps({
        "period": period.upper(),
        "term_id": term,
        "freerooms": get_free_rooms(period, term),
        "classes": [available] * 3, # TODO add support for other terms
        "currentclass": current_class,
        "altperiods": None # TODO add this in UI
    })

### Functions to generate period information

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
    print(occupied)
    return list(free - occupied)

def get_grade_range(grade):
    if not grade:
        return None
    elif grade <= 8: # Middle school
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
        if not key: # Skip free periods
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

'''@app.route('/cron/<job>')
class CronHandler():
    def get(self, job):  # On url invoke
        if job == "lunch":
            update_lunch.read_lunches()
            self.response.write("Success")
        elif job == "schedules": # Warning - takes a LONG time
            json_schedules = fetch_schedules_with_api()'''

# Change and view privacy settings
@app.route('/privacy', methods=['GET', 'POST'])
def handle_settings():
    if 'username' not in session:
        abort(403)
    user = get_database_entry(session["username"])

    if request.method == 'GET':
        return json.dumps(dict(user.items()))

    elif request.method == 'POST':
        print(request.args.get('share_photo'))

        user.update({
            "share_photo": request.form['share_photo'] == "true",
            "share_schedule": request.form['share_schedule'] == "true"
        })
        datastore_client.put(user)
        return json.dumps({})

@app.route('/search/<keyword>')
def handle_search(keyword):
    if 'username' not in session:
        abort(403)

    results = []
    for schedule in get_schedule_data().values():
        test_keyword = schedule["firstname"] + " " + schedule["lastname"]
        if keyword.lower() in test_keyword.lower():
            results.append({"name": test_keyword, "username": schedule["username"]})
            if len(results) >= 5:  # We only display five results
                break
    return json.dumps(results)

