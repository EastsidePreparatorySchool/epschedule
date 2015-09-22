#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import base64
import copy
import json
import jinja2
import os
import string
import logging
import datetime
from google.appengine.ext import db
from google.appengine.ext import vendor
from google.appengine.api import mail

# Add any libraries installed in the "lib" folder.
vendor.add('lib')

# External libraries.
from py_bcrypt import bcrypt
from slowaes import aes
from sendgrid import SendGridClient
from sendgrid import Mail

DEMO_USER = "demo"
DEMO_ID = "9999"
CRYPTO_KEY = open('crypto.key', 'rb').read()
API_KEYS = json.load(open('api_keys.json', 'rb'))
ID_TABLE = json.load(open('id_table.json', 'rb'))
SCHEDULE_INFO = json.load(open('schedules.json', 'rb'))
LAT_LON_COORDS = json.load(open('room_locations.json', 'rb'))
BIOS = json.load(open('bios.json', 'rb'))
JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

class User(db.Model):
    email = db.StringProperty(required=True)
    password = db.StringProperty(required=True)
    join_date = db.DateTimeProperty()
    verified = db.BooleanProperty(required=True)

def convert_email_to_id(email):
    email = email.lower()
    pieces = string.split(email, "@")
    username = pieces[0]
    if username == DEMO_USER:
        return DEMO_ID
    for student in ID_TABLE:
        if (student[0] == username):
            return student[1]
    return None

def normalize_name(name):
    name = name.lower()
    name = name.replace(" ", "")
    name = name.replace(".", "")
    return name

def generate_email(firstname, lastname):
    firstname = normalize_name(firstname)
    lastname = normalize_name(lastname)
    return firstname[0] + lastname + "@eastsideprep.org"

def get_schedule_data():
    return SCHEDULE_INFO

def is_teacher_schedule(schedule):
    return not schedule["grade"]

def create_error_obj(error_message, action="", buttontext=""):
    error_obj = {"error":error_message}
    if action: # If action is present (meaning the error has a button)
        error_obj["action"] = action
        error_obj["buttontext"] = buttontext
    return json.dumps(error_obj)

ERR_SIGNUP_EMAIL_NOT_EPS = {
  "error": "Use your Eastside Prep email account"
}
ERR_UNKNOWN_EMAIL = {
    "error": "Unknown email address"
}
ERR_NOT_ALLOWED_EMAIL = {
    "error": "Invalid email address"
}
ERR_PASSWORD_INVALID_FORMAT = {
  "error": "Your password must be at least eight characters"
}
ERR_EMAIL_ALREADY_REGISTERED = {
  "error": "This email is already registered",
  "action":"/forgot",
  "buttonText":"FORGOT PASSWORD?",
  "actionId":"url"
}
REGISTER_SUCCESS = {
  "error": "Success! Check your email to complete registration"
}

class BaseHandler(webapp2.RequestHandler): # All handlers inherit from this handler
    def check_id(self):
        encoded_id = self.request.cookies.get("SID")
        if encoded_id is None:
            return None
        # TODO add code to check if id is valid
        id = aes.decryptData(CRYPTO_KEY, base64.b64decode(encoded_id))
        return id

    def check_password(self, email, password):  # Returns 0 for all good, returns 1 for correct password but you need to verify the account, returns 2 for incorrect password
        logging.info("Checking passwords")
        account_confirmed = False
        known_username = False

        # If only username is supplied, assume eastsideprep.org.
        if '@' not in email:
            email += "@eastsideprep.org"
        # If a domain is specified, it must be eastsideprep.org.
        if email[-17:] != "@eastsideprep.org":
            return ERR_NOT_EPS_EMAIL

        user_obj_query = db.GqlQuery("SELECT * FROM User WHERE email = :1", email)
        for query_result in user_obj_query:
            known_username = True
            test_hashed_password = bcrypt.hashpw(password, query_result.password)
            logging.info("original: " + query_result.password + " test: " + test_hashed_password)
            password_match = test_hashed_password == query_result.password
            if not password_match:
                return ERR_FORGOT_PASSWORD
            if query_result.verified:
                account_confirmed = True
                break

        if not known_username:
            return ERR_NO_ACCOUNT
        elif not account_confirmed:
            return ERR_UNCONFIRMED_ACCOUNT

        return {}  # success

    def check_signed_up(self, email):           # Returns false if there is already a registered user signed up, returns true if there is not
        user_obj_query = db.GqlQuery("SELECT * FROM User WHERE email = :1 AND verified = TRUE", email)
        for query_result in user_obj_query:
            return False
        return True

    def get_schedule_for_name(self, firstname, lastname):
        schedule_data = get_schedule_data()
        for schedule in schedule_data:
            if normalize_name(schedule['firstname']) == firstname.lower() and \
               normalize_name(schedule['lastname']) == lastname.lower(): # If the schedule is the requested schedule
                return schedule
        return None

    def get_schedule_for_id(self, id):
        schedule_data = get_schedule_data()
        for schedule in schedule_data:
            if schedule["id"] == str(id): # If the schedule is the user's schedule
                return schedule
        return None

ERR_NO_ACCOUNT_TO_SEND = {
  "error": "There is no account with that username and password",
  "action":"switchToRegister",
  "buttonText":"SIGN UP",
  "actionId":"button"
}
class RegisterBaseHandler(BaseHandler):
    def get_name(self, email):
        id = convert_email_to_id(email)

        schedules = get_schedule_data()
        for schedule in schedules:
            if int(schedule['id']) == int(id):
                return schedule['firstname']

    def format_html(self, email_text, obj):
        for prop in obj:
            search = "{" + prop + "}"
            message_parts = string.split(email_text, search)
            email_text = message_parts[0] + obj[prop] + message_parts[1]
        return email_text

    def send_confirmation_email(self, email, row_id):
        email_file = open('confirm_email.html', 'rb')
        email_text = email_file.read()
        email_properties = {
            'name': self.get_name(email),
            'email': email,
            'url': self.get_confirmation_link(row_id)
        }

        creds = API_KEYS['sendgrid']
        client = SendGridClient(creds['username'], creds['password'], secure=True)
        message = Mail()
        message.set_subject("Sign up for EPSchedule")
        message.set_html(self.format_html(email_text, email_properties))
        # message.set_text('plaintext message body')
        # TODO make sender fooy@epscheduleapp.appspot.com
        message.set_from("The EPSchedule Team <gavin.uberti@gmail.com>")
        message.add_to(email)
        logging.info("Sending " + email + " a link to " + email_properties['url'])
        client.send(message)

    def get_confirmation_link(self, row_id):
        encrypted_row_id = aes.encryptData(CRYPTO_KEY, row_id)
        encoded_row_id = base64.urlsafe_b64encode(encrypted_row_id)
        url = "https://www.epschedule.com/confirm/" + encoded_row_id
        return url

class RegisterHandler (RegisterBaseHandler):
    def post(self):
        email = self.request.get('email').lower()
        password = self.request.get('password')

        if email[-17:] != "@eastsideprep.org":
            self.response.write(json.dumps(ERR_SIGNUP_EMAIL_NOT_EPS))
            return

        if not self.check_signed_up(email):
            self.response.write(json.dumps(ERR_EMAIL_ALREADY_REGISTERED))
            return

        id = convert_email_to_id(email)

        if not convert_email_to_id: # If id is None
            self.response.write(json.dumps(ERR_UNKNOWN_EMAIL))
            return

        schedule = self.get_schedule_for_id(id)

        if not schedule:
            self.response.write(json.dumps(ERR_NOT_ALLOWED_EMAIL))
            return

        if len(password) < 8:
            self.response.write(json.dumps(ERR_PASSWORD_INVALID_FORMAT))
            return

        hashed = bcrypt.hashpw(password, bcrypt.gensalt(1))
        user_obj = User(email = email, password = hashed, verified = False)
        user_obj.join_date = datetime.datetime.now()
        db.put(user_obj)
        row_id = str(user_obj.key().id())
        logging.info("row id = " + row_id)
        self.send_confirmation_email(email, row_id)
        self.response.write(json.dumps(REGISTER_SUCCESS))


class ResendEmailHandler(RegisterBaseHandler):
    def post(self):
        email = self.request.get('email').lower()
        password = self.request.get('password')
        user_obj_query = db.GqlQuery("SELECT * FROM User WHERE email = :1 AND verified = FALSE", email)
        for user_obj in user_obj_query:
            if bcrypt.hashpw(password, user_obj.password) == user_obj.password:
                self.send_confirmation_email(email, str(user_obj.key().id()))
                self.response.write(json.dumps(REGISTER_SUCCESS))
                return

        self.response.write(json.dumps(ERR_NO_ACCOUNT_TO_SEND))

class ConfirmHandler(BaseHandler):
    def get(self, encoded_row_id):
        row_id = aes.decryptData(CRYPTO_KEY, base64.urlsafe_b64decode(encoded_row_id))
        logging.info(row_id)
        obj_to_confirm = User.get_by_id(int(row_id)) # FIX Instead of email, use row id
        user_obj_query = db.GqlQuery("SELECT * FROM User WHERE email = :1",obj_to_confirm.email)

        verified = False # Whether the email has a verified entry in the DB

        for user_obj in user_obj_query:
            if user_obj.verified:
                verified = True
                break

        if not verified:
            user_obj_query.verified = True
            user_obj_query.put()
            self.redirect("/")
            return
            # TODO redirect user to main page
        else:
            self.response.write("This account has already been confirmed!")
            # TODO redirect user to schedule page
            return
        self.response.write("Something went wrong! There is no object with row_id " + row_id + " in the database")

ERR_UNCONFIRMED_ACCOUNT = {
  "error": "Your need to confirm your account. Didn't recieve a confirmation email? ",
  "action":"resendConfirmationEmail",
  "buttonText":"RESEND",
  "actionId":"button"
}
ERR_FORGOT_PASSWORD = {
  "error": "Your username or password is incorrect. ",
  "action":"/forgot",
  "buttonText":"FORGOT?",
  "actionId":"url"
}
ERR_NO_ACCOUNT = {
  "error": "That email is not yet registered",
  "action":"switchToRegister",
  "buttonText":"SIGN UP",
  "actionId":"button"
}
ERR_NOT_EPS_EMAIL = {
  "error": "Please sign in with your Eastside Prep email account "
}

class LoginHandler (BaseHandler):
    def post(self):
        email = self.request.get('email').lower()
        password = self.request.get('password')

        err = self.check_password(email, password) # Returns an object, so we don't have to call create_error_obj() on this
        if err:
            self.response.write(json.dumps(err))
        else:
            id = convert_email_to_id(email)
            if id is not None:
                encoded_id = base64.b64encode(aes.encryptData(CRYPTO_KEY, str(id)))
                expiration_date = datetime.datetime.now()
                expiration_date += datetime.timedelta(3650) # Set expiration date 10 years in the future
                self.response.set_cookie('SID', encoded_id, expires=expiration_date)
                self.response.write(create_error_obj(""))
            else:
                self.response.write(create_error_obj("Something went wrong! " + email + " is in the password database, but it is not in schedules.json. Please contact the administrators."))

class ChangePasswordHandler(BaseHandler):
    def post(self):
        id = self.check_id() # TODO check to make sure that the account is associated with the proper id
        if id is None:
            self.error(403)
            return
        elif id == DEMO_ID: # If it is the demo account
            self.response.write(json.dumps({"error":"You are a terrible person."}))
            return
        email = self.get_username(id) + "@eastsideprep.org"
        old_password = self.request.get('oldpassword')
        new_password = self.request.get('newpassword')
        logging.info(email + " would like to change their password")
        err = self.check_password(email, str(old_password))
        if err:
            self.response.write(json.dumps({"error":"Your password is incorrect."}))
        else:
            hashed = bcrypt.hashpw(new_password, bcrypt.gensalt(1))
            user_obj_query = db.GqlQuery("SELECT * FROM User WHERE email = :1 AND verified = TRUE", email)
            for query_result in user_obj_query:
                query_result.password = hashed
                db.put(query_result)
                self.response.write(json.dumps({}))
                break

    def get_username(self, id):
        for id_obj in ID_TABLE:
            if str(id_obj[1]) == id:
                return id_obj[0]
        logging.info("Found no email for id!");
        return None

class LogoutHandler(BaseHandler):
    def post(self):
        self.response.delete_cookie("SID")

class ClassHandler(BaseHandler):
    def get_class_schedule(self, class_name, period):
        schedules = get_schedule_data()
        result = None
        for schedule in schedules:                                    # Load up each student's schedule
            for classobj in schedule['classes']:                      # For each one of their classes
                if classobj['name'].lower().replace(" ", "_").replace(".", "") == class_name.lower() and \
                   classobj['period'].lower() == period.lower():       # Check class name and period match
                    if classobj['teacher'] != "":                     # If they aren't a student (teacher names will be added later)
                        if not result:
                            result = {"period": classobj['period'], \
                                      "teacher": classobj['teacher'], \
                                      "students": []}
                        student = {"firstname": schedule['firstname'], \
                                   "lastname": schedule['lastname'], \
                                   "email": generate_email(schedule['firstname'], schedule['lastname'])}

                        result['students'].append(student)

        result['students'].sort(key=lambda s: s['firstname'])
        return result
    def get(self, class_name, period):
        logging.info("get()")
        # Get the cookie
        id = self.check_id()
        if id is None:
            self.error(403)
            return

        # schedule = self.get_schedule(self.request.get('id'))
        self.response.write(json.dumps(self.get_class_schedule(class_name, period)))

class StudentHandler(BaseHandler):
    def get(self, student_name):
        id = self.check_id()
        if id is None:
            self.error(403)
            return

        if id == str(DEMO_ID):
            id = "4093"

        # Split student_name into firstname and lastname
        student_names = student_name.split("_")
        firstname = student_names[0].lower()
        lastname = student_names[1].lower()
        student_schedule = self.get_schedule_for_name(firstname, lastname)
        user_schedule = self.get_schedule_for_id(id)

        if is_teacher_schedule(user_schedule):
            # If the user is a teacher
            response_schedule = copy.deepcopy(student_schedule)
        else:
            response_schedule = self.sanitize_schedule(student_schedule, user_schedule)

        # Generate email address
        response_schedule["email"] = generate_email(firstname, lastname)

        self.response.write(json.dumps(response_schedule))

    def sanitize_schedule(self, orig_schedule, user_schedule):
        schedule = copy.deepcopy(orig_schedule)
        for i in range (0, len(schedule["classes"])):
            # If the class is not shared among the user and student
            if not self.has_class(user_schedule, schedule["classes"][i]):
                # Sanitize the class
                schedule["classes"][i] = self.sanitize_class(schedule["classes"][i])

        return schedule

    def has_class(self, schedule, input_obj):
        return input_obj in schedule["classes"]

    def sanitize_class(self, orig_class_obj):
        class_obj = orig_class_obj.copy()
        study_halls = ["Study Hall", "GSH", "Free Period"]

        if class_obj["name"] in study_halls:
            class_obj["name"] = "Free Period"
        else:
            class_obj["name"] = "Hidden"

        class_obj["teacher"] = ""
        class_obj["room"] = ""

        return class_obj # Return the class object

class PeriodHandler(BaseHandler):
    def get(self, period):
        id = self.check_id()
        if id is None:
            self.error(403)
            return
        # Should return back which of your teachers are free, which rooms are free, what class you currently have then, and what classes you could take then
        dataobj = {'freeteachers':[], 'freerooms':[], 'currentclass':{}, 'potentialclassschedules':[]}
        if id == DEMO_ID: # If this is the demo accound
            id = "4093"
        schedule_data = get_schedule_data()
        user_schedule = None

        period = period.upper()
        for schedule in schedule_data:
            if schedule['id'] == id:
                user_schedule = schedule
                break
        logging.info("Getting here!")
        for class_obj in user_schedule['classes']: # Find out which class the user has then
            logging.info("Is " + class_obj['period'] + " equal to " + period + "? I guess not!")
            if class_obj['period'] == period:
                dataobj['currentclass'] = class_obj
                logging.info("Writing to currentclass")
                break

        for schedule in schedule_data:
            if schedule['grade'] is None: # If the schedule is a teacher's schedule
                for class_obj in user_schedule['classes']: # For each of your classes
                    if class_obj['teacher'] == (schedule['firstname'] + " " + schedule['lastname']): # If the teacher is one of your teachers
                        is_free = True
                        for taught_class in schedule['classes']:
                            if taught_class['period'] == period:
                                is_free = False
                                break
                        if is_free:
                            dataobj['freeteachers'].append(class_obj['teacher'])

            if schedule['grade'] == user_schedule['grade']: # Get all classes the user could be taking at that point in time
                for class_obj in schedule['classes']:
                    unique = True # Whether the current class is also had by the user
                    for user_class_obj in user_schedule['classes']:
                        if (class_obj == user_class_obj):
                            unique = False
                            break
                    if unique:
                        dataobj['potentialclassschedules'].append(class_obj)

            for class_obj in schedule['classes']: # Get list of periods
                if dataobj['freerooms'].count(class_obj['room']) == 0:
                    dataobj['freerooms'].append(class_obj['room'])

        for schedule in schedule_data: # Find out which periods are free
            for class_obj in schedule['classes']:
                if class_obj['period'] == period:
                    if (dataobj['freerooms'].count(class_obj['room']) > 0):
                        dataobj['freerooms'].remove(class_obj['room'])

        self.response.write(json.dumps(dataobj))

class RoomHandler(BaseHandler):
    def get(self, room):
        id = self.check_id()
        if id is None:
            self.error(403)
            return
        schedules = get_schedule_data()
        room = room.lower()
        room = room.replace('_', '-');
        room_schedule = {'name':room, 'classes':[]}
        for schedule in schedules:
            for class_obj in schedule['classes']:
                if room == class_obj['room'].lower(): # If the class is in the room
                    already_there = False
                    for room_class_obj in room_schedule['classes']:
                        if class_obj == room_class_obj:
                            already_there = True
                    if not already_there:
                        room_schedule['classes'].append(class_obj)

        for room_obj in LAT_LON_COORDS:
            if room_obj['name'] == room:
                room_schedule['latitude'] = room_obj['latitude']
                room_schedule['longitude'] = room_obj['longitude']
                break
        self.response.write(json.dumps(room_schedule))

class TeacherHandler(BaseHandler):
    def get(self, teacher):
        id = self.check_id()
        if id is None:
            self.error(403)
            return
        teacher = teacher.lower()
        bio = self.getBio(teacher)
        schedule_data = get_schedule_data()
        teachernames = string.split(teacher, "_")

        for schedule in schedule_data:
            if schedule['firstname'].lower() == teachernames[0] and schedule['lastname'].lower() == teachernames[1]:
                schedule['email'] = generate_email(schedule['firstname'], schedule['lastname'])
                schedule['bio'] = bio
                self.response.write(json.dumps(schedule))

    def getBio(self, teacher):
        for bio in BIOS:
            if bio['name'] == teacher:
                return bio['bio']
class MainHandler(BaseHandler):
    # def __init__(self):
    def get_schedule(self, id):
        schedules = get_schedule_data();
        for schedule in schedules:
            if schedule['id'] == id:
                return schedule
        return None

    def get_days(self):
        file = open('exceptions.json', 'rb')
        days = json.load(file)
        return days

    def send_login_response(self):
        template_values = {}
        template = JINJA_ENVIRONMENT.get_template('login.html')
        self.response.write(template.render(template_values))

    def get(self):
        # Get the cookie
        id = self.check_id()
        if id is None:
            self.send_login_response()
            return

        logging.info("New request for id: " + id)
        if id == DEMO_ID: # If this is the demo account
            id = "4093"
        # schedule = self.get_schedule(self.request.get('id'))
        schedule = self.get_schedule(id)
        days = self.get_days()
        if schedule is not None:
            template_values = {'schedule':json.dumps(schedule), 'days':json.dumps(days)}
            template = JINJA_ENVIRONMENT.get_template('index.html')
            self.response.write(template.render(template_values))
        else:
            self.response.write("No schedule for id " + id)

class AboutHandler(BaseHandler):
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('about.html')
        self.response.write(template.render({}))

class AdminHandler(RegisterBaseHandler):
    def get(self):
        id = self.check_id()
        if id != "4093":
            self.error(403)
            return

        verification = self.read_db()

        html = "<h1>Stats</h1>"

        html += "<h2>" + str(len(verification))
        html += " unique emails entered</h2>"

        only_verified = sorted([ k for k,v in verification.iteritems() if len(v['verified']) == 1 and len(v['unverified']) == 0 ])
        html += "<h3>" + str(len(only_verified)) + " emails in good condition</h3>"
        for email in only_verified:
            html += email + "<br>"

        verified_and_unverified = sorted([ k for k,v in verification.iteritems() if len(v['verified']) >= 1 and len(v['unverified']) >= 1 ])
        html += "<h3>" + str(len(verified_and_unverified)) + " emails with verified and unverified records</h3>"
        for email in verified_and_unverified:
            html += email + " [" + str(len(verification[email]['unverified'])) + "]<br>"

        only_unverified = sorted([ k for k,v in verification.iteritems() if len(v['verified']) == 0 and len(v['unverified']) >= 1 ])
        html += "<h3>" + str(len(only_unverified)) + " emails with only unverified records</h3>"
        for email in only_unverified:
            email_schedule = self.get_schedule_for_id(convert_email_to_id(email))
            is_valid = "invalid" # Will either be "valid" or "invalid"

            if email_schedule:
                is_valid = "valid"

            html += email + " [" + str(len(verification[email]['unverified'])) + ", " + is_valid + "]<br>"

        multiple_verified = sorted([ k for k,v in verification.iteritems() if len(v['verified']) > 1 ])
        # If there are ever any entries in multiple_verified, the DB is in a very bad state
        if multiple_verified:
            html += "<h3>Attention! There are " + str(len(multiple_verified)) + " emails with more than one verified record. The DB is REALLY messed up!</h3>"
            for email in multiple_verified:
                html += email + " [" + str(len(verification[email]['verified'])) + ", " + str(len(verification[email]['unverified'])) + "]<br>"

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
        html += '"emailblast"'
        html += ")'>Send verification emails to unregistered users</button>"
        html += "<button type='button' onclick='sendEmails("
        html += '"cleanup"'
        html += ")'>Clean up duplicates of confirmed users</button>"
        self.response.write(html)

    def read_db(self): # Returns the entire database as an dictionary

        verification = {}
        query = db.GqlQuery("SELECT * FROM User")
        for query_result in query:
            if not query_result.email in verification:
                verification[query_result.email] = {'verified': [], 'unverified': []}
            # Append the entity's key to the appropriate list
            verification[query_result.email][self.get_key(query_result.verified)].append(query_result.key())

        return verification

    def get_key(self, verified): # A function that takes either True or False and returns either "verified" or "unverified"
        if verified:
            return "verified"
        return "unverified"

    def post(self, action):
        id = self.check_id()
        if id != "4093":
            self.error(403)
            return

        if action == "emailblast":
            logging.info("Email blasting")
            self.send_email_blast()
        elif action == "cleanup":
            logging.info("Cleaning up db")
            self.clean_up_db()

    def send_email_blast(self):
        verification = self.read_db()
        # Generate unverified_row_ids

        for email in verification:
            if len(verification[email]['verified']) == 0:
                numerical_id = verification[email]['unverified'][0].id()
                logging.info("Sending " + email + " a verification email")
                try:
                    error = self.send_confirmation_email(email, numerical_id)
                except: # If email is ficticious or something else went wrong
                    logging.error("Attempt to send an email to " + email + " was unsuccessful")

    def clean_up_db(self):
        verification = self.read_db()
        for email in verification:
            if len(verification[email]['verified']) == 1 and len(verification[email]['unverified']) >= 1:
                db.delete(verification[email]['unverified'])

app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/about', AboutHandler),
    ('/login', LoginHandler),
    ('/logout', LogoutHandler),
    ('/register', RegisterHandler),
    ('/resend', ResendEmailHandler),
    ('/changepassword', ChangePasswordHandler),
    ('/confirm/([\w\-]+)', ConfirmHandler),
    ('/class/([\w\-]+)/([\w\-]+)', ClassHandler),
    ('/period/(\w+)', PeriodHandler),
    ('/room/([\w\-]+)', RoomHandler),
    ('/teacher/([\w\-]+)', TeacherHandler),
    ('/student/([\w\-]+)', StudentHandler),
    ('/admin', AdminHandler),
    ('/admin/(\w+)', AdminHandler)
], debug=True)