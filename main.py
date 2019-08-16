import base64
import copy
import datetime
import json
import logging
import os
import random
import string
import time
from sets import Set

import authenticate_user
import jinja2
import update_lunch
import webapp2
from google.appengine.ext import db, vendor

# Add any libraries installed in the "lib" folder.
vendor.add("lib")

# External libraries.
from Crypto.Hash import SHA256
from slowaes import aes


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


DEMO_USER = "demo"
DEMO_ID = "9999"
GAVIN_ID = "4093"
CRYPTO_KEY = load_data_file("crypto.key", True).strip()
ID_TABLE = load_json_file("id_table.json", True)
SCHEDULE_INFO = load_json_file("schedules.json", True)
BIOS = load_json_file("bios.json")
DAYS = load_json_file("exceptions.json")
JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=["jinja2.ext.autoescape"],
    autoescape=True,
)

FALL_TRI_END = datetime.datetime(2018, 12, 21, 15, 30, 0, 0)
WINT_TRI_END = datetime.datetime(2019, 3, 22, 15, 30, 0, 0)


class User(db.Expando):
    email = db.StringProperty(required=True)
    join_date = db.DateTimeProperty()

    share_photo = db.BooleanProperty(default=False)
    share_schedule = db.BooleanProperty(default=False)
    seen_update_dialog = db.BooleanProperty(default=False)


def convert_email_to_id(email):
    email = email.lower()
    pieces = string.split(email, "@")
    username = pieces[0]
    if username == DEMO_USER:
        return DEMO_ID
    for student in ID_TABLE:
        if student["username"] == username:
            return student["id"]
    return None


# TODO merge with id to username function
def convert_id_to_email(id):
    email = ""

    if str(id) == DEMO_ID:
        email = DEMO_USER

    for student in ID_TABLE:
        if str(student["id"]) == str(id):
            email = student["username"]

    if email == "":
        return None
    else:
        return email + "@eastsideprep.org"


def normalize_name(name):
    name = name.lower()
    name = name.replace(" ", "")
    name = name.replace(".", "")
    return name


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


def generate_email(username):
    return username + "@eastsideprep.org"


def is_teacher_schedule(schedule):
    return not schedule["grade"]


def create_error_obj(error_message):
    return json.dumps({"error": error_message})


class BaseHandler(webapp2.RequestHandler):  # All handlers inherit from this handler
    def get_term_id(self):
        tid = self.request.get("term_id")
        if tid and int(tid) <= 2 and int(tid) >= 0:
            return int(tid)
        else:
            now = datetime.datetime.now()
            if now < FALL_TRI_END:
                return 0
            elif now < WINT_TRI_END:
                return 1
            else:
                return 2

    def get_schedule_data(self):
        return SCHEDULE_INFO

    def gen_photo_url(self, username, folder):
        photo_hasher = SHA256.new(CRYPTO_KEY)

        photo_hasher.update(bytes(username))
        encoded_filename = photo_hasher.hexdigest()

        return "/" + folder + "/" + encoded_filename + ".jpg"

    def decrypt_id(self, encoded_id):
        return aes.decryptData(CRYPTO_KEY, base64.b64decode(encoded_id))

    def check_id(self):
        encoded_id = self.request.cookies.get("SID")
        if not encoded_id:
            return None
        # TODO add code to check if id is valid
        return self.decrypt_id(encoded_id)

    def check_admin_id(self):
        return self.check_id() == GAVIN_ID

    def query_by_email(self, email):
        return db.GqlQuery("SELECT * FROM User WHERE email = :1", email)

    def get_schedule_for_name(self, firstname, lastname):
        schedule_data = self.get_schedule_data()
        for schedule in schedule_data:
            if (
                normalize_name(schedule["firstname"]) == firstname.lower()
                and normalize_name(schedule["lastname"]) == lastname.lower()
            ):  # If the schedule is the requested schedule
                return schedule
        return None

    def get_schedule_for_id(self, id):
        schedule_data = self.get_schedule_data()
        for schedule in schedule_data:
            if schedule["sid"] == int(id):  # If the schedule is the user's schedule
                return schedule
        return None

    def get_components_filename(self):
        if self.request.get("vulcanize", "1") == "0":
            filename = "components.html"
        else:
            filename = "vulcanized.html"
        return filename


class LoginHandler(BaseHandler):
    def post(self):
        email = self.request.get("email").lower()
        password = self.request.get("password")

        id = convert_email_to_id(email)

        if not id:  # If there is no id for the email, don't try to log in
            self.response.write(json.dumps({"error": "That email is not recognized."}))
            return

        username = string.split(email, "@")[0]

        if email == "demo" and password == "demo":
            id = GAVIN_ID
            email = "guberti@eastsideprep.org"
            pass
        elif not (
            authenticate_user.auth_user(username + "@eastsideprep.org", password)
        ):  # If four11 authentication failed, return our error
            self.response.write(json.dumps({"error": "Your password is incorrect."}))
            return

        # If authentication was successful, check to see if the person has an EPSchedule account
        user_obj_query = self.query_by_email(email)
        if not user_obj_query.get():
            student_obj = User(
                email=username + "@eastsideprep.org", join_date=datetime.datetime.now()
            )
            student_obj.put()

        # If the authentication was successful, give the user an auth token

        id = convert_email_to_id(email)
        if id is not None:
            encoded_id = base64.b64encode(aes.encryptData(CRYPTO_KEY, str(id)))
            expiration_date = datetime.datetime.now()
            expiration_date += datetime.timedelta(
                3650
            )  # Set expiration date 10 years in the future
            self.response.set_cookie("SID", encoded_id, expires=expiration_date)
            self.response.write(create_error_obj(""))
        else:
            self.response.write(
                create_error_obj(
                    "Something went wrong! "
                    + email
                    + " is in the password database, but it is not in schedules.json. Please contact the administrators."
                )
            )


class LunchIdLoginHandler(BaseHandler):
    def post(self):
        username = self.request.get("username").lower()
        password = self.request.get("password")

        ID = convert_email_to_id(username + "@eastsideprep.org")
        logging.info(username + "@eastsideprep.org")
        if not ID:
            self.error(403)
            self.response.write("No ID!")
            return
        # If four11 authentication failed, return our error
        if not (authenticate_user.auth_user(username + "@eastsideprep.org", password)):
            self.error(403)
            self.response.write("Wrong password!")
            return

        schedule = self.get_schedule_for_id(ID)
        if schedule["gradyear"]:
            lunch_code = str(schedule["gradyear"]) + str(ID)
        else:
            lunch_code = str(10000000 + ID)
        photo_url = self.gen_photo_url(schedule["username"], "96x96_photos")

        obj = {
            "code": lunch_code,
            "photo": photo_url,
            "updateKey": base64.b64encode(aes.encryptData(CRYPTO_KEY, str(id))),
        }

        self.response.write(json.dumps(obj))


class LunchIdUpdateHandler(BaseHandler):
    def get(self):
        # id = decryptData(self.request.get("updateKey"))
        # if id is None:
        #    self.error(403)
        #    return
        lunches = update_lunch.get_all_future_lunches(datetime.datetime.now())
        self.response.write(json.dumps(lunches))


class LogoutHandler(BaseHandler):
    def post(self):
        self.response.delete_cookie("SID")
        self.response.delete_cookie("SEENPRIVDIALOG")
        self.response.write(json.dumps({}))


class ClassHandler(BaseHandler):
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

    def get_class_schedule(self, user_class, term_id):
        schedules = self.get_schedule_data()
        result = {
            "period": user_class["period"],
            "teacher": user_class["teacher"],
            "term_id": term_id,
            "students": [],
        }

        opted_out = self.gen_opted_out_table()

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

                        email = generate_email(schedule["username"])
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
            result["students"].sort(key=lambda s: s["firstname"])
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

        result = self.get_class_schedule(clss, term_id)
        if not result:
            self.error(404)
            return

        self.response.write(json.dumps(result))


class StudentHandler(BaseHandler):
    def get(self, username):
        id = self.check_id()
        if id is None:
            self.error(403)
            return

        if id == str(DEMO_ID):
            id = GAVIN_ID

        email = username + "@eastsideprep.org"
        show_full_schedule = True
        show_photo = True
        user_obj_query = self.query_by_email(email)
        user_obj = user_obj_query.get()

        if user_obj:
            show_full_schedule = user_obj.share_schedule
            show_photo = user_obj.share_photo

        sid = convert_email_to_id(email)
        student_schedule = self.get_schedule_for_id(sid)

        if is_teacher_schedule(student_schedule):
            show_photo = True

        if not student_schedule:
            self.error(404)
            return

        user_schedule = self.get_schedule_for_id(id)

        if (
            is_teacher_schedule(user_schedule)
            or show_full_schedule
            or is_teacher_schedule(student_schedule)
        ):
            # If the user is a teacher
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
        altperiods = Set()
        freerooms = Set()

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

        self.response.write(json.dumps(dataobj))


class TeacherHandler(BaseHandler):
    def get(self, teacher):
        id = self.check_id()
        if id is None:
            self.error(403)
            return

        if id == DEMO_ID:  # If this is the demo account
            id = GAVIN_ID

        teacher = teacher.lower()
        bio = self.get_bio(teacher)
        if not bio:
            bio = ""
        schedule_data = self.get_schedule_data()
        teachernames = string.split(teacher, "_")
        result = None

        for schedule in schedule_data:
            if (
                schedule["firstname"].lower() == teachernames[0]
                and schedule["lastname"].lower() == teachernames[1]
            ):
                result = copy.deepcopy(schedule)
                result["email"] = generate_email(schedule["username"])
                result["bio"] = bio

        if not result:
            self.error(404)
            return

        self.response.write(json.dumps(result))

    def get_bio(self, teacher):
        for bio in BIOS:
            if bio["name"] == teacher:
                return bio["bio"]


class MainHandler(BaseHandler):
    # def __init__(self):
    def get_schedule(self, id):
        schedules = self.get_schedule_data()
        for schedule in schedules:
            if schedule["sid"] == int(id):
                return schedule
        return None

    def send_login_response(self):
        template_values = {"components": self.get_components_filename()}
        template = JINJA_ENVIRONMENT.get_template("login.html")
        self.response.write(template.render(template_values))

    def get(self):
        # Get the cookie
        id = self.check_id()
        if id is None:
            self.send_login_response()
            return

        if id == DEMO_ID:  # If this is the demo account
            id = GAVIN_ID
        # schedule = self.get_schedule(self.request.get('id'))
        schedule = self.get_schedule(id)
        lunch_objs = update_lunch.getLunchForDate(datetime.date.today())

        if schedule is not None:

            show_privacy_dialog = False

            if self.request.cookies.get("SEENPRIVDIALOG") != "1":
                if schedule["grade"]:  # If the user is a student
                    user_obj_query = self.query_by_email(convert_id_to_email(id))
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


ERR_NO_LUNCH_TO_RATE = {"error": "You cannot rate today's lunch"}

ORIG_LUNCH_RATE = {"error": "Your vote has been recorded"}

LUNCH_RATE_OVERWRITE = {"error": "Your vote has been updated"}


class LunchRateHandler(BaseHandler):
    def post(self):
        id = int(self.check_id())
        if id is None:
            self.error(403)
            return

        date = datetime.datetime.now()

        lunch_id = update_lunch.get_lunch_id_for_date(date)

        if not lunch_id:  # If there is no lunch for the date
            self.response.write(json.dumps(ERR_NO_LUNCH_TO_RATE))
            return

        rating = int(self.request.get("rating"))
        overwrote = update_lunch.place_rating(rating, id, lunch_id, date)
        if overwrote:
            self.response.write(json.dumps(LUNCH_RATE_OVERWRITE))
        else:
            self.response.write(json.dumps(ORIG_LUNCH_RATE))


class AboutHandler(BaseHandler):
    def get(self):
        template_values = {"components": self.get_components_filename()}
        template = JINJA_ENVIRONMENT.get_template("about.html")
        self.response.write(template.render(template_values))


class AdminHandler(BaseHandler):
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
        html += '"emaildomainadd"'
        html += ")'>Add domains to emails</button>"
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


class CronHandler(BaseHandler):
    def get(self, job):  # On url invoke
        if job == "lunch":
            update_lunch.read_lunches()
            self.response.write("Success")


class PrivacyHandler(BaseHandler):  # Change and view privacy settings
    def load_obj(self):
        id = self.check_id()
        if id is None:
            return None

        email = convert_id_to_email(id)
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


class AvatarHandler(BaseHandler):
    def get(self, user):
        if not self.check_admin_id():
            self.error(403)
            return
        args = string.split(user, "_")
        url = self.gen_photo_url(args[1], args[0], "school_photos")
        self.redirect(url)


class SearchHandler(BaseHandler):
    def get(self, keyword):
        results = []
        for schedule in self.get_schedule_data():
            test_keyword = schedule["firstname"] + " " + schedule["lastname"]
            if keyword.lower() in test_keyword.lower():
                results.append({"name": test_keyword, "username": schedule["username"]})
                if len(results) >= 5:  # We only display five results
                    break

        self.response.write(json.dumps(results))


app = webapp2.WSGIApplication(
    [
        ("/", MainHandler),
        ("/about", AboutHandler),
        ("/avatar/(\w+).jpg", AvatarHandler),
        ("/login", LoginHandler),
        ("/logout", LogoutHandler),
        ("/privacy", PrivacyHandler),
        ("/class/(\w+)", ClassHandler),
        ("/period/(\w+)", PeriodHandler),
        ("/teacher/([\w\-]+)", TeacherHandler),
        ("/student/([\w\-]+)", StudentHandler),
        ("/lunch", LunchRateHandler),
        ("/admin", AdminHandler),
        ("/admin/(\w+)", AdminHandler),
        ("/search/(.*)", SearchHandler),
        ("/cron/(\w+)", CronHandler),
        ("/lunchid", LunchIdLoginHandler),
        ("/lunchupdate", LunchIdUpdateHandler),
    ],
    debug=True,
)
