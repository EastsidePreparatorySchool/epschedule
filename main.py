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
import binascii
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
    for student in ID_TABLE:
        if (student[0] == username):
            return student[1]
    return None

def load_schedule_data():
    file = open('schedules.json', 'rb')
    schedules = json.load(file)
    return schedules

class RegisterHandler (webapp2.RequestHandler):
    def post(self):
        email = self.request.get('email')
        password = self.request.get('password')
        
        if email[-17:] != "@eastsideprep.org":
            self.response.write("Please sign up with your Eastside Prep email account.")             #TODO redirect user to custom error page
            logging.error(email[-17:])
            return
        
        if not self.check_signed_up(email):
            self.response.write("This email has already been registered!")            #TODO redirect user to 'email has already been registered' page
            return
        
        self.response.write("Success! Check your email to complete registration.")   #TODO redirect user to custom success page
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
    
    def send_confirmation_email(self, email, row_id):       #TODO customize message to include the user's name
        message = mail.EmailMessage()
        message.sender = "The EPSchedule Team"
        message.to = email
        message.subject = "Sign up for EPSchedule"
        message.body = self.get_confirmation_link(row_id)
        logging.info("Sending " + email + " a link to " + message.body)
        message.send()
        
    def get_confirmation_link(self, row_id):
        encoded_row_id = binascii.hexlify(aes.encryptData(CRYPTO_KEY, row_id))
        url = "epscheduleapp.appspot.com/confirm/" + encoded_row_id
        return url
    
    def get(self):
        #      TODO redirect user to main schedule page if they have a auth cookie
        #template_values = {'schedule':json.dumps(schedule), 'days':json.dumps(days)}
        template_values = {}
        template = JINJA_ENVIRONMENT.get_template('signup.html')
        self.response.write(template.render(template_values))

class ConfirmHandler(webapp2.RequestHandler):
    def get(self, encoded_row_id):
        logging.info("Trying to confirm!")
        row_id = aes.decryptData(CRYPTO_KEY, binascii.unhexlify(encoded_row_id))
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
        
class LoginHandler (webapp2.RequestHandler):
    def post(self):
        email = self.request.get('email')
        password = self.request.get('password')
        password_valid = self.check_password(email, password)
        if password_valid == 1:
            self.response.write("You need to confirm your account")
        elif password_valid == 2:
            self.response.write("Your username or password is incorrect")
        else:
            id = convert_email_to_id(email)
            if id is not None:
                encoded_id = base64.b64encode(aes.encryptData(CRYPTO_KEY, str(id)))
                self.response.set_cookie('SID', encoded_id)
                self.redirect("/")
            else:
                self.response.write("Something went wrong! " + email + " is in the password database, but it is not in schedules.json. Please contact the administrators.")
    
    def check_password(self, email, password):  #Returns 0 for all good, returns 1 for correct password but you need to verify the account, returns 2 for incorrect password
        logging.info("Checking passwords")
        user_obj_query = db.GqlQuery("SELECT * FROM User WHERE email = :1", email)
        for query_result in user_obj_query:
            test_hashed_password = bcrypt.hashpw(password, query_result.password)
            logging.info("original: " + query_result.password + " test: " + test_hashed_password)
            password_match = test_hashed_password == query_result.password
            if password_match:
                if query_result.verified:
                    return 0
                return 1
        return 2
        
class ClassHandler(webapp2.RequestHandler):
    def get_class_schedule(self, classname):
        schedules = load_schedule_data();
        classdataobj = []
        for schedule in schedules:                                    #Load up each student's schedule
            for classobj in schedule['classes']:                      #For each one of their classes
                if classobj['name'].lower() == classname:             #If that classes' name is the same as the class name we're looking for
                    if classobj['teacher'] != "":                     #If they aren't a student (teacher names will be added later)

                        createnewperiod = True                        #Assume that we need to create a new period
                        for period in classdataobj:                   #For each period that we know the target class is held in
                            if period['period'] == classobj['period']:#If that period is the same as the period
                                createnewperiod = False               #We know that we don't need to create a new period

                        if createnewperiod:                           #If we need to create a new period, create one and set the teacher
                            classdataobj.append({"period":classobj['period'], "teacher":classobj['teacher'], "students":[]})

                        for i in range (0, len(classdataobj)):                             #For each known period in the class
                            if classdataobj[i]['period'] == classobj['period']:            #If the student belongs in that period
                                name = schedule['firstname'] + " " + schedule['lastname']  #Append their name to a list of students in that period
                                classdataobj[i]['students'].append(name)
        return classdataobj
    def get(self, class_id):
        #Get the cookie
        encoded_id = self.request.cookies.get("SID")
        if encoded_id is None:
            self.send_login_response()
            return

        id = aes.decryptData(CRYPTO_KEY, base64.b64decode(encoded_id))
        #schedule = self.get_schedule(self.request.get('id'))
        self.response.write(self.get_class_schedule(class_id))

class MainHandler(webapp2.RequestHandler):
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
        encoded_id = self.request.cookies.get("SID")
        if encoded_id is None:
            self.send_login_response()
            return

        id = aes.decryptData(CRYPTO_KEY, base64.b64decode(encoded_id))
        #schedule = self.get_schedule(self.request.get('id'))
        schedule = self.get_schedule(id)
        days = self.get_days()
        if schedule is not None:
            template_values = {'schedule':json.dumps(schedule), 'days':json.dumps(days)}
            template = JINJA_ENVIRONMENT.get_template('index.html')
            self.response.write(template.render(template_values))
        else:
            self.response.write("No schedule for id " + id)


app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/login', LoginHandler),
    ('/register',RegisterHandler),
    ('/confirm/(\w+)',ConfirmHandler),
    ('/class/(\w+)', ClassHandler)
], debug=True)

