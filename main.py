import base64
import copy
import datetime
import json
import logging
import os
from os import path
import string
import time
import hashlib

from flask import Flask, render_template, request, session, make_response
from google.auth.transport import requests
from google.cloud import datastore, secretmanager
import google.oauth2.id_token

app = Flask(__name__)
app.permanent_session_lifetime = datetime.timedelta(days=3650)


# Get application secret key
os.environ["GOOGLE_APPLICATION_CREDENTIALS"]="epschedule-455d8a10f5ec.json"
secret_client = secretmanager.SecretManagerServiceClient()
app.secret_key = secret_client.access_secret_version("projects/epschedule-v2/secrets/session_key/versions/1").payload.data

def open_data_file(filename, has_test_data=False):
    if has_test_data and "EPSCHEDULE_USE_TEST_DATA" in os.environ:
        fullname = "data/test_" + filename
    else:
        fullname = "data/" + filename
    return open(fullname, "rb")


def load_data_file(filename, has_test_data=False):
    return open_data_file(filename, has_test_data).read()


def load_json_file(filename, has_test_data=False):
    return json.load(open_data_file(filename, has_test_data))

CRYPTO_KEY = load_data_file("crypto.key", True).strip()
ID_TABLE = load_json_file("id_table.json", True)
SCHEDULE_INFO = load_json_file("schedules.json", True)
DAYS = load_json_file("exceptions.json")

FALL_TRI_END = datetime.datetime(2019, 11, 23, 15, 30, 0, 0)
WINT_TRI_END = datetime.datetime(2020, 3, 6, 15, 30, 0, 0)

def normalize_classname(text):
    text = text.lower()
    punctuation = set(string.punctuation + " ")
    clean_text = ""
    for character in text:
        if character not in punctuation:
            clean_text += character
        else:
            clean_text += "_"
    return clean_text

def username_to_email(username):
    return username + "@eastsideprep.org"

def is_teacher_schedule(schedule):
    return not schedule["grade"]

def create_error_obj(error_message):
    return json.dumps({"error": error_message})

def get_term_id(self):
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

def gen_photo_url(self, username, folder):
    photo_hasher = hashlib.sha256(CRYPTO_KEY)
    photo_hasher.update(bytes(username))
    encoded_filename = photo_hasher.hexdigest()
    return "/" + folder + "/" + encoded_filename + ".jpg"

def query_by_email(self, email):
    return db.GqlQuery("SELECT * FROM User WHERE email = :1", email)

def get_components_filename(self):
    if self.request.get("vulcanize", "1") == "0":
        filename = "components.html"
    else:
        filename = "vulcanized.html"
    return filename

@app.route('/logout')
class LogoutHandler():
    def post(self):
        self.response.delete_cookie("SID")
        self.response.write(json.dumps({}))

'''@app.route('/class/<period>')
class ClassHandler():
    def gen_opted_out_table(self):
        table = set()
        opted_out = db.GqlQuery("SELECT * FROM User WHERE share_photo = FALSE")
        for student in opted_out:
            table.add(student.email)

        return table

    def is_same_class(self, a, b):
        return (
            normalize_classname(a["name"]) == normalize_classname(b["name"])
            and a["period"] == b["period"]
            and a["teacher"] == b["teacher"]
            and a["room"] == b["room"]
        )

    def get_class_schedule(self, user_class, term_id, censor=True):
        schedules = self.get_schedule_data()
        result = {
            "period": user_class["period"],
            "teacher": user_class["teacher"],
            "term_id": term_id,
            "students": [],
        }

        if censor:
            opted_out = self.gen_opted_out_table()
        else:
            opted_out = set()

        for schedule in schedules:  # Load up each student's schedule
            for classobj in schedule["classes"][
                term_id
            ]:  # For each one of their classes
                if self.is_same_class(
                    user_class, classobj
                ):  # Check class name and period match

                    if (
                        schedule["gradyear"] or classobj["name"] == "Free Period"
                    ):  # If they are a student or it is a free period
                        if not result:
                            result = {
                                "period": classobj["period"],
                                "teacher": classobj["teacher"],
                                "students": [],
                            }

                        email = username_to_email(schedule["username"])
                        photo_url = self.gen_photo_url(
                            schedule["username"], "96x96_photos"
                        )

                        if email in opted_out:
                            photo_url = (
                                "/images/placeholder_small.png"
                            )  # Default placeholder

                        student = {
                            "firstname": schedule["firstname"],
                            "lastname": schedule["lastname"],
                            "grade": schedule["grade"],
                            "email": email,
                            "photo_url": photo_url,
                        }

                        # Lines below are for creating the demo, but are no longer used

                        # teacher_schedule = self.get_teacher_photo(random.randint(1, 40))
                        # logging.info("Is this null? Firstname is: " + teacher_schedule['firstname'])

                        # student = {"firstname": teacher_schedule['firstname'], \
                        #           "lastname": teacher_schedule['lastname'], \
                        #           "email": email,
                        #           "photo_url": "/96x96_photos/" + teacher_schedule["firstname"] + "_" + teacher_schedule["lastname"] + ".jpg"}

                        result["students"].append(student)

        if result:
            result["students"] = sorted(
                sorted(result["students"], key = lambda s: s["firstname"]),
                key = lambda s: bool(s["grade"]))
            #sorts alphabetically, then sorts teachers from students
        return result

    def get(self, period):
        # Get the cookie
        id = self.check_id()
        if id is None:
            self.error(403)
            return

        if id == DEMO_ID:
            id = GAVIN_ID

        term_id = self.get_term_id()
        user_schedule = self.get_schedule_for_id(id)

        clss = next(
            (
                c
                for c in user_schedule["classes"][term_id]
                if c["period"].lower() == period
            )
        )

        censor = not is_teacher_schedule(user_schedule)
        result = self.get_class_schedule(clss, term_id, censor=censor)
        if not result:
            self.error(404)
            return

        self.response.write(json.dumps(result))

@app.route('/student/<username>')
class StudentHandler(BaseHandler):
    def get(self, username):
        id = self.check_id()
        if id is None:
            self.error(403)
            return

        if id == str(DEMO_ID):
            id = GAVIN_ID

        email = username_to_email(username)
        show_full_schedule = True
        show_photo = True

        user_obj = self.query_by_email(email).get()

        if user_obj:
            show_full_schedule = user_obj.share_schedule
            show_photo = user_obj.share_photo

        sid = username_to_id(username)
        student_schedule = self.get_schedule_for_id(sid)
        if not student_schedule:
            self.error(404)
            return

        user_schedule = self.get_schedule_for_id(id)

        if (is_teacher_schedule(user_schedule) or
            is_teacher_schedule(student_schedule)):
            show_photo = True
            show_full_schedule = True

        if show_full_schedule:
            response_schedule = copy.deepcopy(student_schedule)
        else:
            response_schedule = self.sanitize_schedule(student_schedule, user_schedule)

        # Generate email address
        response_schedule["email"] = email

        if show_photo:
            response_schedule["photo_url"] = self.gen_photo_url(
                username, "school_photos"
            )
        else:
            response_schedule["photo_url"] = "/images/placeholder.png"

        self.response.write(json.dumps(response_schedule))

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
class PeriodHandler(BaseHandler):
    def get(self, period):
        id = self.check_id()
        if id is None:
            self.error(403)
            return

        if id == DEMO_ID:  # If this is the demo account
            id = GAVIN_ID

        # Should return back which of your teachers are free,
        # which rooms are free, what class you currently have then,
        # and what classes you could take then
        dataobj = {"classes": []}
        altperiods = set()
        freerooms = set()

        if id == DEMO_ID:  # If this is the demo account
            id = GAVIN_ID
        schedule_data = self.get_schedule_data()
        user_schedule = None
        user_class = None
        term_id = self.get_term_id()

        period = period.upper()

        # Get user's schedule
        for schedule in schedule_data:
            if schedule["sid"] == int(id):
                user_schedule = schedule
                break

        for class_obj in user_schedule["classes"][
            term_id
        ]:  # Find out which class the user has then
            if class_obj["period"] == period:
                user_class = class_obj
                break

        for schedule in schedule_data:
            if schedule["grade"] == user_schedule["grade"]:
                # For each person in the user's grade:

                # Get what class they have in the period in question
                testclass = {}
                for clss in schedule["classes"][term_id]:
                    if clss["period"] == period and clss["name"] != "Free Period":
                        testclass = clss
                        break

                if testclass:
                    # Test if we already have an appropriate object
                    newobjectneeded = True

                    for clss in dataobj["classes"]:
                        if (
                            clss["name"] == testclass["name"]
                            and clss["period"] == testclass["period"]
                        ):
                            newobjectneeded = False
                            break

                    if newobjectneeded:
                        if not user_schedule["grade"]:
                            testclass = copy.copy(testclass)
                            testclass["teacher"] = (
                                schedule["firstname"] + " " + schedule["lastname"]
                            )

                        dataobj["classes"].append(testclass)

                        dataobj["classes"][-1]["students"] = 0

            for class_obj in schedule["classes"][term_id]:

                # For each class, add its room to our room set
                freerooms.add(class_obj["room"])

                # For each class, if it's the same class that
                # we have that period but in a different period,
                # add that to "other periods" list
                if class_obj["name"] == user_class["name"]:
                    altperiods.add(class_obj["period"])

        for schedule in schedule_data:  # Find out which rooms are free
            if not schedule["grade"]:
                continue
            for clss in schedule["classes"][term_id]:
                if clss["period"] == period:
                    for test_class in dataobj["classes"]:

                        if normalize_classname(
                            test_class["name"]
                        ) == normalize_classname(clss["name"]):
                            test_class["students"] += 1

                    freerooms.discard(clss["room"])

        # List comprehension to remove duplicate classes
        # While it would also be possible to do this with a for loop,
        # the fastest way is list comprehension
        dataobj["classes"] = map(
            dict,
            set(tuple(sorted(potclass.items())) for potclass in dataobj["classes"]),
        )

        for clss in reversed(dataobj["classes"]):
            if not clss["room"]:
                dataobj["classes"].remove(clss)

        for clss in dataobj["classes"]:
            # We already know periods are the same
            if (
                clss["name"] == user_class["name"]
                and clss["room"] == user_class["room"]
            ):
                dataobj["currentclass"] = clss
                dataobj["classes"].remove(clss)
                break

        if "currentclass" not in dataobj:
            dataobj["currentclass"] = {
                "name": "Free Period",
                "period": period,
                "room": None,
                "teacher": None,
            }

        altperiods.remove(user_class["period"])

        dataobj["period"] = period
        dataobj["freerooms"] = sorted(list(freerooms))
        dataobj["classes"].sort(key=lambda x: x["name"])
        dataobj["altperiods"] = sorted(list(altperiods))
        dataobj["term_id"] = term_id

        classes_for_trimester = dataobj["classes"]
        dataobj["classes"] = [None, None, None]
        dataobj["classes"][term_id] = classes_for_trimester

        self.response.write(json.dumps(dataobj))'''

def gen_login_response():
    template = make_response(render_template("login.html", components="static/components.html"))
    # Clear all cookies
    session.pop('username', None)
    template.set_cookie('token', '', expires=0)
    return template

def get_schedule(username):
    schedule_data = get_schedule_data()
    for schedule in schedule_data:
        if schedule["username"] == username:  # If the schedule is the user's schedule
            return schedule
    return None


firebase_request_adapter = requests.Request()

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

def get(self):
    # Get the cookie
    id = self.check_id()
    if id is None:
        self.send_login_response()
        return

    # schedule = self.get_schedule(self.request.get('id'))
    schedule = self.get_schedule(id)
    lunch_objs = update_lunch.getLunchForDate(datetime.date.today())

    if schedule is not None:

        show_privacy_dialog = False

        if self.request.cookies.get("SEENPRIVDIALOG") != "1":
            if schedule["grade"]:  # If the user is a student
                user_obj_query = self.query_by_email(id_to_email(id))
                obj = user_obj_query.get()
                if obj:
                    show_privacy_dialog = not obj.seen_update_dialog
            if not show_privacy_dialog:
                expiration_date = datetime.datetime.now()
                expiration_date += datetime.timedelta(
                    3650
                )  # Set expiration date 10 years in the future
                self.response.set_cookie(
                    "SEENPRIVDIALOG", "1", expires=expiration_date
                )

        # Handler for how to serialize date objs into json
        template_values = {
            "schedule": json.dumps(schedule),
            "days": json.dumps(DAYS),
            "components": self.get_components_filename(),
            "lunches": json.dumps(lunch_objs),
            "self_photo": json.dumps(
                self.gen_photo_url(schedule["username"], "school_photos")
            ),
            "show_privacy_dialog": json.dumps(show_privacy_dialog),
            # Multiply by 1000 to give Unix time in milliseconds
            "fall_end_unix": str(int(time.mktime(FALL_TRI_END.timetuple())) * 1000),
            "wint_end_unix": str(int(time.mktime(WINT_TRI_END.timetuple())) * 1000),
        }

        template = JINJA_ENVIRONMENT.get_template("index.html")
        self.response.write(template.render(template_values))
    else:
        self.response.write("No schedule for id " + id)

'''class AdminHandler(BaseHandler):
    def get(self):
        if not self.check_admin_id():
            self.error(403)
            return

        data = self.read_db()

        html = "<h1>Stats</h1>"

        html += "<h2>" + str(len(data))
        html += " unique emails entered</h2>"

        num_four11 = len({k: v for (k, v) in data.iteritems() if not v.get("password")})
        num_seen_dialog = len(
            {k: v for (k, v) in data.iteritems() if v.get("seen_update_dialog")}
        )
        num_share_photo = len(
            {k: v for (k, v) in data.iteritems() if v.get("share_photo")}
        )
        num_share_schedule = len(
            {k: v for (k, v) in data.iteritems() if v.get("share_schedule")}
        )

        percent_seen_dialog = 0
        percent_share_photo = 0
        percent_share_schedule = 0
        if len(data) > 0:
            percent_seen_dialog = num_seen_dialog * 100 / len(data)
        if num_seen_dialog > 0:
            percent_share_photo = num_share_photo * 100 / num_seen_dialog
            percent_share_schedule = num_share_schedule * 100 / num_seen_dialog

        # html += "<h3>" + str(len(only_verified_list)) + " emails in good condition</h3>"
        # for email in only_verified_list:
        #    html += email + "<br>"
        html += (
            str(num_seen_dialog)
            + " ("
            + str(percent_seen_dialog)
            + "%) have seen privacy dialog<br>"
        )
        html += (
            str(num_share_photo)
            + " ("
            + str(percent_share_photo)
            + "%) sharing their photo<br>"
        )
        html += (
            str(num_share_schedule)
            + " ("
            + str(percent_share_schedule)
            + "%) sharing their schedule</h4>"
        )

        multiple_entities = sorted([k for k, v in data.iteritems() if len(v) > 1])
        # If there are ever any entries in multiple_verified, the DB is in a very bad state
        if multiple_entities:
            html += (
                "<h3>Attention! There are "
                + str(len(multiple_entities))
                + " emails with more than one record. The DB is REALLY messed up!</h3>"
            )
            for email in multiple_entities:
                html += email + "<br>"

        html += """
        <script>
          function sendEmails(action) {
            window.alert("Performing " + action + ", press OK to continue");
            xhr = new XMLHttpRequest();
            xhr.onreadystatechange = function() {
              if (xhr.readyState == 4 && xhr.status == 200) {
                setTimeout(reloadPage, 3000);
              }
            }
            xhr.open('POST', 'admin/' + action, true);
            xhr.send();
          }
          function reloadPage() {
            location.reload();
          }
        </script>"""
        html += "<button type='button' onclick='sendEmails("
        html += '"addschoolyear"'
        html += ")'>Add new school year</button>"
        html += "<button type='button' onclick='sendEmails("
        html += '"cleanup"'
        html += ")'>Clean up duplicates of confirmed users</button>"
        html += "<button type='button' onclick='sendEmails("
        html += '"removeoutdated"'
        html += ")'>Remove outdated columns</button>"
        self.response.write(html)

    # Returns the entire database as a dictionary
    def read_db(self):
        data = {}
        query = db.GqlQuery("SELECT * FROM User ORDER BY join_date ASC")
        for query_result in query:
            if not query_result.email in data:
                data[query_result.email] = {
                    "seen_update_dialog": False,
                    "share_photo": False,
                    "share_schedule": False,
                    "hits": [],
                }

            data[query_result.email]["hits"].append(query_result)
            if query_result.seen_update_dialog:
                data[query_result.email]["seen_update_dialog"] = True
            if query_result.share_photo:
                data[query_result.email]["share_photo"] = True
            if query_result.share_schedule:
                data[query_result.email]["share_schedule"] = True

        return data

    def post(self, action):
        if not self.check_admin_id():
            self.error(403)
            return

        if action == "cleanup":
            self.clean_up_db()
        elif action == "emaildomainadd":
            self.email_domain_add()
        elif action == "removeoutdated":
            self.remove_outdated_props()
        elif action == "addschoolyear":
            self.create_new_year_object()

    # Removes and merges duplicates
    def clean_up_db(self):
        data = self.read_db()
        for email, obj in data.iteritems():
            # Update the main object
            obj["hits"][0].seen_update_dialog = obj["seen_update_dialog"]
            obj["hits"][0].share_photo = obj["share_photo"]
            obj["hits"][0].share_schedule = obj["share_schedule"]
            obj["hits"][0].put()

            for i in range(1, len(obj["hits"])):
                obj["hits"][i].delete()

    def email_domain_add(self):
        query = db.GqlQuery("SELECT * FROM User")
        for query_result in query:
            if "@eastsideprep.org" not in query_result.email:
                query_result.email += "@eastsideprep.org"
                query_result.put()

    def remove_outdated_props(self):
        query = db.GqlQuery("SELECT * FROM User WHERE verified = True")
        for query_result in query:
            for prop in ["password", "verified"]:
                if hasattr(query_result, prop):
                    delattr(query_result, prop)
                    query_result.put()
                    logging.info("Removed password from user " + query_result["email"])

    def create_new_year_object(self):
        year_obj = SchoolYear(
            schedules={'test': 1}
        )
        year_obj.put()
'''
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
        self.response.write(json.dumps({}))

@app.route('/search/<keyword>')
class SearchHandler(BaseHandler):
    def get(self, keyword):
        results = []
        for schedule in self.get_schedule_data():
            test_keyword = schedule["firstname"] + " " + schedule["lastname"]
            if keyword.lower() in test_keyword.lower():
                results.append({"name": test_keyword, "username": schedule["username"]})
                if len(results) >= 5:  # We only display five results
                    break

        self.response.write(json.dumps(results))'''

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
