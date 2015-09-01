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
from slowaes import aes
from py_bcrypt import bcrypt

CRYPTO_KEY = open('crypto.key', 'rb').read()
id_table_file = open('id_table.json', 'rb')
ID_TABLE = json.load(id_table_file)
schedule_info_file = open('schedules.json', 'rb')
SCHEDULE_INFO = json.load(schedule_info_file)
lat_lon_coords_file = open('room_locations.json', 'rb')
LAT_LON_COORDS = json.load(lat_lon_coords_file)
bios_file = open('bios.json', 'rb')
BIOS = json.load(bios_file)
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
    if email == "demo@eastsideprep.org":
        return 9999
    pieces = string.split(email, "@")
    username = pieces[0]
    for student in ID_TABLE:
        if (student[0] == username):
            return student[1]
    return None

def load_schedule_data():
    return SCHEDULE_INFO

def create_error_obj(error_message, action="", buttontext=""):
    error_obj = {"error":error_message}
    if action: #If action is present (meaning the error has a button)
        error_obj["action"] = action
        error_obj["buttontext"] = buttontext
    return json.dumps(error_obj)

ERR_SIGNUP_EMAIL_NOT_EPS = {
  "error": "Use your Eastside Prep email account"
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

class BaseHandler(webapp2.RequestHandler): #All handlers inherit from this handler
    def check_id(self):
        encoded_id = self.request.cookies.get("SID")
        if encoded_id is None:
            return None
        #TODO add code to check if id is valid
        id = aes.decryptData(CRYPTO_KEY, base64.b64decode(encoded_id))
        return id

    def check_password(self, email, password):  #Returns 0 for all good, returns 1 for correct password but you need to verify the account, returns 2 for incorrect password
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

class RegisterHandler (BaseHandler):
    def post(self):
        email = self.request.get('email')
        password = self.request.get('password')

        if email[-17:] != "@eastsideprep.org":
            self.response.write(json.dumps(ERR_SIGNUP_EMAIL_NOT_EPS))
            return

        if not self.check_signed_up(email):
            self.response.write(json.dumps(ERR_EMAIL_ALREADY_REGISTERED))
            return

        self.response.write(json.dumps(REGISTER_SUCCESS))
        hashed = bcrypt.hashpw(password, bcrypt.gensalt(1))
        user_obj = User(email = email, password = hashed, verified = False)
        user_obj.join_date = datetime.datetime.now()
        db.put(user_obj)
        row_id = str(user_obj.key().id())
        logging.info("row id = " + row_id)
        self.send_confirmation_email(email, row_id)

    def check_signed_up(self, email):           #Returns false if there is already a registered user signed up, returns true if there is not
        user_obj_query = db.GqlQuery("SELECT * FROM User WHERE email = :1 AND verified = TRUE", email)
        for query_result in user_obj_query:
            return False
        return True

    def get_name(self, email):
        id = None
        for id_pair in ID_TABLE:
            if id_pair[0] + "@eastsideprep.org" == email:
                id = id_pair[1]
                break

        schedules = load_schedule_data()
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
        email_properties = {}
        email_properties['name'] = self.get_name(email)
        email_properties['email'] = email
        email_properties['url'] = self.get_confirmation_link(row_id)
        message = mail.EmailMessage()
        message.sender = "The EPSchedule Team <gavin.uberti@gmail.com>"   #TODO make sender fooy@epscheduleapp.appspot.com
        message.to = email
        message.subject = "Sign up for EPSchedule"
        message.html = self.format_html(email_text, email_properties)
        logging.info("Sending " + email + " a link to " + email_properties['url'])
        message.send()

    def get_confirmation_link(self, row_id):
        encrypted_row_id = aes.encryptData(CRYPTO_KEY, row_id)
        encoded_row_id = base64.urlsafe_b64encode(encrypted_row_id)
        url = "http://epscheduleapp.appspot.com/confirm/" + encoded_row_id
        return url

class ConfirmHandler(BaseHandler):
    def get(self, encoded_row_id):
        row_id = aes.decryptData(CRYPTO_KEY, base64.urlsafe_b64decode(encoded_row_id))
        logging.info(row_id)
        user_obj_query = User.get_by_id(int(row_id)) #FIX Instead of email, use row id
        if not user_obj_query.verified:
            user_obj_query.verified = True
            user_obj_query.put()
            self.redirect("/")
            return
            #TODO redirect user to main page
        else:
            self.response.write("This account has already been confirmed!")
            #TODO redirect user to schedule page
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
        email = self.request.get('email')
        password = self.request.get('password')

        err = self.check_password(email, password) #Returns an object, so we don't have to call create_error_obj() on this
        if err:
            self.response.write(json.dumps(err))
        else:
            id = convert_email_to_id(email)
            if id is not None:
                encoded_id = base64.b64encode(aes.encryptData(CRYPTO_KEY, str(id)))
                self.response.set_cookie('SID', encoded_id)
                self.response.write(create_error_obj(""))
            else:
                self.response.write(create_error_obj("Something went wrong! " + email + " is in the password database, but it is not in schedules.json. Please contact the administrators."))

class ChangePasswordHandler(BaseHandler):
    def post(self):
        id = self.check_id() #TODO check to make sure that the account is associated with the proper id
        if id is None:
            self.error(403)
            return
        elif id == "9999": #If it is the demo account
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
        schedules = load_schedule_data()
        result = None
        for schedule in schedules:                                    #Load up each student's schedule
            for classobj in schedule['classes']:                      #For each one of their classes
                if classobj['name'].lower().replace(" ", "_").replace(".", "") == class_name.lower() and \
                   classobj['period'].lower() == period.lower():       #Check class name and period match
                    if classobj['teacher'] != "":                     #If they aren't a student (teacher names will be added later)
                        if not result:
                            result = {"period": classobj['period'], \
                                      "teacher": classobj['teacher'], \
                                      "students": []}
                        student = {"firstname": schedule['firstname'], \
                                   "lastname": schedule['lastname'], \
                                   "email": "nobody@eastsideprep.org"}  #Append their name to a list of students in that period
                        result['students'].append(student)

        result['students'].sort(key=lambda s: s['firstname'])
        return result
    def get(self, class_name, period):
        logging.info("get()")
        #Get the cookie
        id = self.check_id()
        if id is None:
            self.error(403)
            return

        #schedule = self.get_schedule(self.request.get('id'))
        self.response.write(json.dumps(self.get_class_schedule(class_name, period)))

class StudentHandler(BaseHandler):
    def get(self, student_name):
        id = self.check_id()
        if id is None:
            self.error(403)
            return
        student_names = student_name.split("_") #Replace spaces with underscores, to get from 'first_last' to 'first last'
        firstname = student_names[0].lower()
        lastname = student_names[1].lower()
        schedules = load_schedule_data()
        for schedule in schedules:
            if schedule['firstname'].lower() == firstname and \
            schedule['lastname'].lower() == lastname:
                self.response.write(json.dumps(schedule))


class PeriodHandler(BaseHandler):
    def get(self, period):
        id = self.check_id()
        if id is None:
            self.error(403)
            return
        #Should return back which of your teachers are free, which rooms are free, what class you currently have then, and what classes you could take then
        dataobj = {'freeteachers':[], 'freerooms':[], 'currentclass':{}, 'potentialclassschedules':[]}
        if id == "9999": #If this is the demo accound
            id = "4093"
        schedule_data = load_schedule_data()
        user_schedule = None

        period = period.upper()
        for schedule in schedule_data:
            if schedule['id'] == id:
                user_schedule = schedule
                break
        logging.info("Getting here!")
        for class_obj in user_schedule['classes']: #Find out which class the user has then
            logging.info("Is " + class_obj['period'] + " equal to " + period + "? I guess not!")
            if class_obj['period'] == period:
                dataobj['currentclass'] = class_obj
                logging.info("Writing to currentclass")
                break

        for schedule in schedule_data:
            if schedule['grade'] is None: #If the schedule is a teacher's schedule
                for class_obj in user_schedule['classes']: #For each of your classes
                    if class_obj['teacher'] == (schedule['firstname'] + " " + schedule['lastname']): #If the teacher is one of your teachers
                        is_free = True
                        for taught_class in schedule['classes']:
                            if taught_class['period'] == period:
                                is_free = False
                                break
                        if is_free:
                            dataobj['freeteachers'].append(class_obj['teacher'])

            if schedule['grade'] == user_schedule['grade']: #Get all classes the user could be taking at that point in time
                for class_obj in schedule['classes']:
                    unique = True #Whether the current class is also had by the user
                    for user_class_obj in user_schedule['classes']:
                        if (class_obj == user_class_obj):
                            unique = False
                            break
                    if unique:
                        dataobj['potentialclassschedules'].append(class_obj)

            for class_obj in schedule['classes']: #Get list of periods
                if dataobj['freerooms'].count(class_obj['room']) == 0:
                    dataobj['freerooms'].append(class_obj['room'])

        for schedule in schedule_data: #Find out which periods are free
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
        schedules = load_schedule_data()
        room = room.lower()
        room = room.replace('_', '-');
        room_schedule = {'name':room, 'classes':[]}
        for schedule in schedules:
            for class_obj in schedule['classes']:
                if room == class_obj['room'].lower(): #If the class is in the room
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
        schedule_data = load_schedule_data()
        teachernames = string.split(teacher, "_")

        for schedule in schedule_data:
            if schedule['firstname'].lower() == teachernames[0] and schedule['lastname'].lower() == teachernames[1]:
                schedule['bio'] = bio
                self.response.write(json.dumps(schedule))

    def getBio(self, teacher):
        for bio in BIOS:
            if bio['name'] == teacher:
                return bio['bio']
class MainHandler(BaseHandler):
    #def __init__(self):
    def get_schedule(self, id):
        schedules = load_schedule_data();
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
        #Get the cookie
        id = self.check_id()
        if id is None:
            self.send_login_response()
            return
        if id == "9999": #If this is the demo account
            id = "4093"
        #schedule = self.get_schedule(self.request.get('id'))
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

app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/about', AboutHandler),
    ('/login', LoginHandler),
    ('/logout', LogoutHandler),
    ('/register', RegisterHandler),
    ('/changepassword', ChangePasswordHandler),
    ('/confirm/([\w\-]+)', ConfirmHandler),
    ('/class/([\w\-]+)/([\w\-]+)', ClassHandler),
    ('/period/(\w+)', PeriodHandler),
    ('/room/([\w\-]+)', RoomHandler),
    ('/teacher/([\w\-]+)', TeacherHandler),
    ('/student/([\w\-]+)', StudentHandler)
], debug=True)