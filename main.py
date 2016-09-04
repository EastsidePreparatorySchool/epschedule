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
import base64
import webapp2
import copy
import json
import jinja2
import os
import string
import logging
import datetime
import update_lunch
import authenticate_user
import random

from google.appengine.ext import db
from google.appengine.ext import vendor

# Add any libraries installed in the "lib" folder.
vendor.add('lib')

# External libraries.
from py_bcrypt import bcrypt
from slowaes import aes
from sendgrid import SendGridClient
from sendgrid import Mail
from Crypto.Hash import SHA256

def open_data_file(filename, has_test_data = False):
    if has_test_data and 'EPSCHEDULE_USE_TEST_DATA' in os.environ:
        fullname = 'data/test_' + filename
    else:
        fullname = 'data/' + filename
    return open(fullname, 'rb')
def load_data_file(filename, has_test_data = False):
    return open_data_file(filename, has_test_data).read()
def load_json_file(filename, has_test_data = False):
    return json.load(open_data_file(filename, has_test_data))

DEMO_USER = "demo"
DEMO_ID = "9999"
CRYPTO_KEY = load_data_file('crypto.key', True).strip()
API_KEYS = load_json_file('api_keys.json', True)
ID_TABLE = load_json_file('id_table.json', True)
SCHEDULE_INFO = load_json_file('schedules.json', True)
LAT_LON_COORDS = load_json_file('room_locations.json')
BIOS = load_json_file('bios.json')
DAYS = load_json_file('exceptions.json')
JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

class User(db.Model):
    email = db.StringProperty(required=True)
    password = db.StringProperty()
    join_date = db.DateTimeProperty()
    verified = db.BooleanProperty(required=True)

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
        if (student[0] == username):
            return student[1]
    return None

def convert_id_to_email(id):
    email = ""

    if str(id) == DEMO_ID:
        email = DEMO_USER


    for student in ID_TABLE:
        logging.info(student[1])
        if (student[1] == str(id)):
            email = student[0]

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
USE_FOUR11_AUTH = {
    "error": "There is no password associated with this account"
}
REGISTER_SUCCESS = {
  "error": "Success! Check your email to complete registration"
}

class BaseHandler(webapp2.RequestHandler): # All handlers inherit from this handler
    def gen_photo_url(self, firstname, lastname, folder):
        input_data = (lastname + "_" + firstname).lower().replace(" ", "")

        photo_hasher = SHA256.new(CRYPTO_KEY)

        photo_hasher.update(input_data)
        encoded_filename = photo_hasher.hexdigest()

        logging.info(input_data + " --> " + encoded_filename)

        return ('/' + folder + '/' + encoded_filename + '.jpg')

    def check_id(self):
        encoded_id = self.request.cookies.get("SID")
        if not encoded_id:
            return None
        # TODO add code to check if id is valid
        id = aes.decryptData(CRYPTO_KEY, base64.b64decode(encoded_id))
        return id

    def check_password(self, email, password):
        # Returns 0 for all good,
        # returns 1 for correct password but you need to verify the account,
        # returns 2 for incorrect password
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
            logging.info(query_result.password)
            if not query_result.password:
                return USE_FOUR11_AUTH
            known_username = True
            logging.info("Password is: " + str(password))
            test_hashed_password = bcrypt.hashpw(password, query_result.password)
            logging.info("Hashed password is: " + str(test_hashed_password))
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

    def check_signed_up(self, email):
        # Returns false if there is already a registered user signed up, returns true if there is not
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

    def get_components_filename(self):
        if self.request.get('vulcanize', '1') == '0':
            filename = 'components.html'
        else:
            filename = 'vulcanized.html'
        return filename

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
        encrypted_row_id = aes.encryptData(CRYPTO_KEY, str(row_id))
        encoded_row_id = base64.urlsafe_b64encode(encrypted_row_id)
        # Use the correct URL depending on where the app is running.
        scheme = 'https'
        host = os.getenv('HTTP_HOST')
        if host.find('localhost') == 0:
            scheme = 'http'
        url = "{0}://{1}/confirm/{2}".format(scheme, host, encoded_row_id)
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

        obj_to_confirm = User.get_by_id(int(row_id)) # Note: Instead of email, use row id

        if not obj_to_confirm: # If entity referenced in the email was deleted
            self.response.write("This account has already been confirmed!")
            self.error(400)
            return
        elif obj_to_confirm.verified:
            self.response.write("This row id has already been confirmed!")
            self.error(400)
            return

        obj_to_confirm.verified = True
        obj_to_confirm.put()

        self.redirect("/")

        user_obj_query = db.GqlQuery("SELECT * FROM User WHERE email = :1", obj_to_confirm.email)
        for user_obj in user_obj_query:
            if user_obj.key() != obj_to_confirm.key():
                if not user_obj.verified:
                    logging.info("Found extra unverified account under " + obj_to_confirm.email)
                    user_obj.delete()
                else:
                    logging.error("Found multiple verified accounts under " + obj_to_confirm.email)
                    logging.error("You should fix that, or add some code to prevent it in the future")

ERR_UNCONFIRMED_ACCOUNT = {
  "error": "Your need to confirm your account. Didn't receive a confirmation email? ",
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

        id = convert_email_to_id(email)

        if not id: # If there is no id for the email, don't try to log in
            self.response.write(json.dumps(ERR_NOT_EPS_EMAIL))
            return

        err = self.check_password(email, password) # Returns an object, so we don't have to call create_error_obj() on this

        if err:
            # If we got an error, try authenticating the user with four11 (slower, so we should use our own auth first)
            username = string.split(email, "@")[0]

            if not (authenticate_user.auth_user(username, password)): # If four11 authentication failed, return our error
                self.response.write(json.dumps(err))
                return


            # If authentication was successful, check to see if the person has an EPSchedule account
            has_account = False
            user_obj_query = db.GqlQuery("SELECT * FROM User WHERE email = :1 AND verified = TRUE", email) # Combine this with password lookup to make it faster
            for query_result in user_obj_query:
                has_account = True

            if not has_account:
                student_obj = User(email = email, verified = True, join_date = datetime.datetime.now())
                student_obj.put()

        # If the authentication was successful, give the user an auth token

        id = convert_email_to_id(email)
        if id is not None:
            encoded_id = base64.b64encode(aes.encryptData(CRYPTO_KEY, str(id)))
            expiration_date = datetime.datetime.now()
            expiration_date += datetime.timedelta(3650) # Set expiration date 10 years in the future
            self.response.set_cookie('SID', encoded_id, expires=expiration_date)
            self.response.write(create_error_obj(""))
        else:
            self.response.write(create_error_obj("Something went wrong! " + \
                email + " is in the password database, but it is not in schedules.json. Please contact the administrators."))

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
        return None

class LogoutHandler(BaseHandler):
    def post(self):
        self.response.delete_cookie("SID")
        self.response.delete_cookie("SEENPRIVDIALOG")
        self.response.write(json.dumps({}))

class ClassHandler(BaseHandler):
    def gen_opted_in_table(self):
        table = {}
        opted_in = db.GqlQuery("SELECT * FROM User WHERE share_photo = TRUE")
        for student in opted_in:
            table[student.email] = student.share_photo

        return table

    def get_teacher_photo(self, num):
        for schedule in get_schedule_data():
            if not schedule["grade"]: # If they are a teacher
                num -= 1
                if num <= 0:
                    logging.info("Returning schedule, firstname is: " + schedule['firstname'])
                    return schedule

    def get_class_schedule(self, class_name, period):
        schedules = get_schedule_data()
        result = None
        logging.info("Starting DB query")
        opted_in = self.gen_opted_in_table()
        logging.info("Finished DB query")

        for schedule in schedules: # Load up each student's schedule
            for classobj in schedule['classes']: # For each one of their classes
                if normalize_classname(classobj['name']) == class_name.lower() and \
                    classobj['period'].lower() == period.lower(): # Check class name and period match
                    if classobj['teacher'] != "" or classobj['name'] == "Free Period": # If they are a student or it is a free period
                        if not result:
                            result = {"period": classobj['period'], \
                                      "teacher": classobj['teacher'], \
                                      "students": []}
                            continue # Don't add teachers to the student list

                        email = generate_email(schedule['firstname'], schedule['lastname'])
                        photo_url = "/images/placeholder_small.png" # Default placeholder

                        if email in opted_in:
                                photo_url = self.gen_photo_url(schedule['firstname'], schedule['lastname'], '96x96_photos')

                        student = {"firstname": schedule['firstname'], \
                                   "lastname": schedule['lastname'], \
                                   "email": email,
                                   "photo_url": photo_url}


                        # Lines below are for creating the demo, but are no longer used

                        #teacher_schedule = self.get_teacher_photo(random.randint(1, 40))
                        #logging.info("Is this null? Firstname is: " + teacher_schedule['firstname'])

                        #student = {"firstname": teacher_schedule['firstname'], \
                        #           "lastname": teacher_schedule['lastname'], \
                        #           "email": email,
                        #           "photo_url": "/96x96_photos/" + teacher_schedule["firstname"] + "_" + teacher_schedule["lastname"] + ".jpg"}

                        result['students'].append(student)

        result['students'].sort(key=lambda s: s['firstname'])
        logging.info("Finished handling request")
        return result
    def get(self, class_name, period):
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

        show_full_schedule = False
        show_photo = False
        email = firstname[0] + lastname + "@eastsideprep.org"
        user_obj_query = db.GqlQuery("SELECT * FROM User WHERE email = :1", email)

        for user_obj in user_obj_query:
            show_full_schedule = user_obj.share_schedule
            show_photo = user_obj.share_photo

        student_schedule = self.get_schedule_for_name(firstname, lastname)
        user_schedule = self.get_schedule_for_id(id)

        if is_teacher_schedule(user_schedule) or show_full_schedule:
            # If the user is a teacher
            response_schedule = copy.deepcopy(student_schedule)
        else:
            response_schedule = self.sanitize_schedule(student_schedule, user_schedule)

        # Generate email address
        response_schedule["email"] = generate_email(firstname, lastname)

        if show_photo:
            logging.info("Args: [" + firstname + ", " + lastname + "]")
            response_schedule["photo_url"] = self.gen_photo_url(firstname, lastname, 'school_photos')
        else:
            response_schedule["photo_url"] = "/images/placeholder.png"

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
        # Should return back which of your teachers are free,
        # which rooms are free, what class you currently have then,
        # and what classes you could take then
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
        for class_obj in user_schedule['classes']: # Find out which class the user has then
            if class_obj['period'] == period:
                dataobj['currentclass'] = class_obj
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

    def send_login_response(self):
        template_values = { 'components': self.get_components_filename() }
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
        lunch_objs = update_lunch.getLunchForDate(datetime.date.today())
        if schedule is not None:

            show_privacy_dialog = False

            if self.request.cookies.get("SEENPRIVDIALOG") != "1":

                if schedule['grade']: # If the user is a student
                    user_obj_query = db.GqlQuery("SELECT * FROM User WHERE email = :1", convert_id_to_email(id))
                    for obj in user_obj_query:
                        show_privacy_dialog = not obj.seen_update_dialog

                if not show_privacy_dialog:
                    expiration_date = datetime.datetime.now()
                    expiration_date += datetime.timedelta(3650) # Set expiration date 10 years in the future
                    self.response.set_cookie('SEENPRIVDIALOG', "1", expires=expiration_date)

            # Handler for how to serialize date objs into json
            template_values = { \
              'schedule': json.dumps(schedule), \
              'days': json.dumps(DAYS), \
              'components': self.get_components_filename(), \
              'lunches': json.dumps(lunch_objs), \
              'self_photo': json.dumps(self.gen_photo_url(schedule["firstname"], schedule["lastname"], "school_photos")), \
              'show_privacy_dialog': json.dumps(show_privacy_dialog) \
            }

            template = JINJA_ENVIRONMENT.get_template('index.html')
            self.response.write(template.render(template_values))
        else:
            self.response.write("No schedule for id " + id)

ERR_NO_LUNCH_TO_RATE = {
  "error": "You cannot rate today's lunch"
}

ORIG_LUNCH_RATE = {
  "error": "Your vote has been recorded"
}

LUNCH_RATE_OVERWRITE = {
  "error": "Your vote has been updated"
}

class LunchRateHandler(BaseHandler):
    def post(self):
        id = int(self.check_id())
        if id is None:
            self.error(403)
            return

        logging.info(self.request.get('rating'));
        #date = datetime.datetine.now()
        date = datetime.date(2016, 3, 10);
        lunch_id = update_lunch.get_lunch_id_for_date(date)

        if not lunch_id: # If there is no lunch for the date
            self.response.write(json.dumps(ERR_NO_LUNCH_TO_RATE))
            return

        rating = int(self.request.get('rating'))
        overwrote = update_lunch.place_rating(rating, id, lunch_id, date)
        if (overwrote):
            self.response.write(json.dumps(LUNCH_RATE_OVERWRITE))
        else:
            self.response.write(json.dumps(ORIG_LUNCH_RATE))

class AboutHandler(BaseHandler):
    def get(self):
        template_values = { 'components': self.get_components_filename() }
        template = JINJA_ENVIRONMENT.get_template('about.html')
        self.response.write(template.render(template_values))

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
            self.send_email_blast()
        elif action == "cleanup":
            self.clean_up_db()

    def send_email_blast(self):
        verification = self.read_db()
        # Generate unverified_row_ids

        for email in verification:
            if len(verification[email]['verified']) == 0:
                numerical_id = verification[email]['unverified'][0].id()
                try:
                    email_schedule = self.get_schedule_for_id(convert_email_to_id(email))
                    if email_schedule:
                        self.send_confirmation_email(email, numerical_id)
                        logging.info("Successfully sent an email to " + email)
                    else:
                        logging.info("There is no valid schedule associated with " + email + ", no email was sent")
                except Exception as e: # If email is ficticious or something else went wrong
                    logging.error("Attempt to send an email to " + email + " was unsuccessful, ", e)

    def clean_up_db(self):
        verification = self.read_db()
        for email in verification:
            if len(verification[email]['verified']) == 1 and len(verification[email]['unverified']) >= 1:
                db.delete(verification[email]['unverified'])

class CronHandler(BaseHandler):
    def get(self, job): # On url invoke
        if job == "lunch":
            update_lunch.read_lunches()
            self.response.write("Success")

class PrivacyHandler(BaseHandler): # Change and view privacy settings
    def load_obj(self):
        id = self.check_id()
        logging.info(id)
        if id is None:
            return None

        email = convert_id_to_email(id)

        user_obj_query = db.GqlQuery("SELECT * FROM User WHERE email = :1 AND verified = TRUE", email)
        for user_obj in user_obj_query:
            return user_obj

    def unicode_to_boolean(self, string):
        if (string == 'true'):
            return True
        elif (string == 'false'):
            return False
        return None

    def get(self):
        user_obj = self.load_obj()
        if user_obj is None:
            self.error(403)
            return 

        response = {"share_photo": user_obj.share_photo, "share_schedule": user_obj.share_schedule}

        expiration_date = datetime.datetime.now()
        expiration_date += datetime.timedelta(3650) # Set expiration date 10 years in the future
        self.response.set_cookie('SEENPRIVDIALOG', "1", expires=expiration_date)

        self.response.write(json.dumps(response))

    def post(self):
        user_obj = self.load_obj()
        if user_obj is None:
            self.error(403)
            return

        user_obj.share_photo = self.unicode_to_boolean(self.request.get('share_photo'))
        user_obj.share_schedule = self.unicode_to_boolean(self.request.get('share_schedule'))
        user_obj.seen_update_dialog = True;
        user_obj.put()
        self.response.write(json.dumps({}))

class AvatarHandler(BaseHandler):
    def get(self, user):
        id = self.check_id()
        if id != "4093":
            self.error(403)
            return
            
        args = string.split(user, '_')
        url = self.gen_photo_url(args[1], args[0], 'school_photos')
        self.redirect(url)

class SearchHandler(BaseHandler):
    def get_url_prefix(self, grade):
        if grade:
            return "student"
        else:
            return "teacher"

    def get(self, keyword):
        RESULTS_TO_RETURN = 5 

        results = []
        for schedule in SCHEDULE_INFO:
            test_keyword = schedule['firstname'] + " " + schedule['lastname']
            if keyword.lower() in test_keyword.lower():
                results.append({"name": test_keyword, "prefix": self.get_url_prefix(schedule['grade'])})


        self.response.write(json.dumps(results))


app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/about', AboutHandler),
    ('/avatar/(\w+).jpg', AvatarHandler),
    ('/login', LoginHandler),
    ('/logout', LogoutHandler),
    ('/register', RegisterHandler),
    ('/resend', ResendEmailHandler),
    ('/changepassword', ChangePasswordHandler),
    ('/confirm/([\w\-=]+)', ConfirmHandler),
    ('/class/([\w\-]+)/([\w\-]+)', ClassHandler),
    ('/period/(\w+)', PeriodHandler),
    ('/room/([\w\-]+)', RoomHandler),
    ('/teacher/([\w\-]+)', TeacherHandler),
    ('/student/([\w\-]+)', StudentHandler),
    ('/lunch', LunchRateHandler),
    ('/admin', AdminHandler),
    ('/search/(.*)', SearchHandler),
    ('/admin/(\w+)', AdminHandler),
    ('/cron/(\w+)', CronHandler),
    ('/privacy', PrivacyHandler),
], debug=True)