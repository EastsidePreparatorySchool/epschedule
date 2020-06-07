import copy
import datetime
import json
import os
import time

from flask import Flask, render_template, request, session, make_response
from google.auth.transport import requests
from google.cloud import storage, secretmanager
import google.oauth2.id_token

from cron.photos import hash_username

app = Flask(__name__)
app.permanent_session_lifetime = datetime.timedelta(days=3650)
# Used to authenticate auth tokens
firebase_request_adapter = requests.Request()


# Authenticate ourselves
os.environ["GOOGLE_APPLICATION_CREDENTIALS"]="epschedule-455d8a10f5ec.json"

# Get application secret key
secret_client = secretmanager.SecretManagerServiceClient()
app.secret_key = secret_client.access_secret_version("projects/epschedule-v2/secrets/session_key/versions/1").payload.data

storage_client = storage.Client()
data_bucket = storage_client.bucket("epschedule-data")
photo_bucket_endpoint = "https://epschedule-avatars.storage.googleapis.com/{}"

def load_json_file(filename):
    blob = data_bucket.blob(filename)
    return json.loads(blob.download_as_string())

SCHEDULE_INFO = load_json_file("schedules.json")
DAYS = load_json_file("exceptions.json")

FALL_TRI_END = datetime.datetime(2019, 11, 23, 15, 30, 0, 0)
WINT_TRI_END = datetime.datetime(2020, 3, 6, 15, 30, 0, 0)

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

def query_by_email(email):
    return db.GqlQuery("SELECT * FROM User WHERE email = :1", email)

def get_components_filename():
    if self.request.get("vulcanize", "1") == "0":
        filename = "components.html"
    else:
        filename = "vulcanized.html"
    return filename

def gen_photo_url(username, icon=False):
    return photo_bucket_endpoint.format(hash_username(app.secret_key, username, icon))

def gen_login_response():
    template = make_response(render_template("login.html", components="static/components.html"))
    # Clear all cookies
    session.pop('username', None)
    template.set_cookie('token', '', expires=0)
    return template

def get_schedule(username):
    for schedule in get_schedule_data():
        if schedule["username"] == username:  # If the schedule is the user's schedule
            return schedule
    return None

@app.route('/')
def main():
    # Tokens are used during login, but after that we use our own system
    # If they have a token, we should always eat it and give them either
    # a proper auth cookie or the login page

    token = request.cookies.get("token")
    if token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(
                token, firebase_request_adapter)
            session.permanent = True
            session['username'] = claims['email'].split("@")[0]
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
        return gen_login_response()

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
    schedules = get_schedule_data()
    result = {
        "period": user_class["period"],
        "teacher": user_class["teacher"],
        "term_id": term_id,
        "students": [],
    }

    opted_out = set()

    for schedule in schedules:  # Load up each student's schedule
        for classobj in schedule["classes"][term_id]:
            if is_same_class(user_class, classobj):
                # We only include teacher schedules in free periods
                if (not is_teacher_schedule(schedule)) or classobj["name"] == "Free Period":

                    if schedule["username"] not in opted_out:
                        photo_url = gen_photo_url(schedule["username"], True)
                    else:
                        photo_url = "/static/images/placeholder_small.png"
                    student = {
                        "firstname": schedule["firstname"],
                        "lastname": schedule["lastname"],
                        "grade": schedule["grade"],
                        "email": username_to_email(schedule["username"]),
                        "photo_url": photo_url,
                    }
                    result["students"].append(student)

    # Sorts alphabetically, then sorts teachers from students
    result["students"] = sorted(
        sorted(result["students"], key = lambda s: s["firstname"]),
        key = lambda s: s["grade"])
    return result


# TODO rename this to /user since it's for students and teachers
@app.route('/student/<target_user>')
def handle_user(target_user):
    if 'username' not in session:
        return gen_login_response()

    # TODO finish privacy logic
    user_schedule = get_schedule(session['username'])
    target_schedule = get_schedule(target_user)

    if is_teacher_schedule(user_schedule) or is_teacher_schedule(target_schedule):
        show_full_schedule = True
        show_photo = True
    else:
        # TODO finish privacy logic
        show_full_schedule = True
        show_photo = True

    if not show_full_schedule:
        target_schedule = sanitize_schedule(target_schedule, user_schedule)

    # Generate email address
    target_schedule["email"] = username_to_email(target_user)

    if show_photo:
        target_schedule["photo_url"] = gen_photo_url(target_user, False)
    else:
        target_schedule["photo_url"] = "/images/placeholder.png"

    return json.dumps(target_schedule)

def sanitize_schedule(self, orig_schedule, user_schedule):
    schedule = copy.deepcopy(orig_schedule)
    for i in range(0, len(schedule["classes"])):
        for k in range(0, len(schedule["classes"][i])):
            # If the class is not shared among the user and student
            if not schedule["classes"][i][k] in user_schedule["classes"][i]:
                # Sanitize the class
                schedule["classes"][i][k] = self.sanitize_class(
                    schedule["classes"][i][k]
                )

    return schedule

def sanitize_class(self, orig_class_obj):
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
        return gen_login_response()

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
    for schedule in get_schedule_data():
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
    for schedule in get_schedule_data():
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



'''# Change and view privacy settings
@app.route('/settings')
class SettingsHandler():
    def load_obj(self):
        id = self.check_id()
        if id is None:
            return None

        email = id_to_email(id)
        user_obj_query = self.query_by_email(email)
        return user_obj_query.get()

    def string_to_boolean(self, string):
        if string == "true":
            return True
        elif string == "false":
            return False
        return None

    def get(self):
        user_obj = self.load_obj()
        if user_obj is None:
            self.error(403)
            return

        response = {
            "share_photo": user_obj.share_photo,
            "share_schedule": user_obj.share_schedule,
        }

        expiration_date = datetime.datetime.now()
        expiration_date += datetime.timedelta(
            3650
        )  # Set expiration date 10 years in the future
        self.response.set_cookie("SEENPRIVDIALOG", "1", expires=expiration_date)

        self.response.write(json.dumps(response))

    def post(self):
        user_obj = self.load_obj()
        if user_obj is None:
            self.error(403)
            return

        user_obj.share_photo = self.string_to_boolean(self.request.get("share_photo"))
        user_obj.share_schedule = self.string_to_boolean(
            self.request.get("share_schedule")
        )
        user_obj.seen_update_dialog = True
        user_obj.put()
        self.response.write(json.dumps({}))'''

@app.route('/search/<keyword>')
def handle_search(keyword):
    results = []
    for schedule in get_schedule_data():
        test_keyword = schedule["firstname"] + " " + schedule["lastname"]
        if keyword.lower() in test_keyword.lower():
            results.append({"name": test_keyword, "username": schedule["username"]})
            if len(results) >= 5:  # We only display five results
                break
    return json.dumps(results)

if __name__ == '__main__':
    # Only used for running locally

    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.
    # Flask's development server will automatically serve static files in
    # the "static" directory. See:
    # http://flask.pocoo.org/docs/1.0/quickstart/#static-files. Once deployed,
    # App Engine itself will serve those files as configured in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)
