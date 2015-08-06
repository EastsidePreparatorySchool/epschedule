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

from google.appengine.ext import vendor
# Add any libraries installed in the "lib" folder.
vendor.add('lib')

# External libraries.
from slowaes import aes
from py_bcrypt import bcrypt

CRYPTO_KEY = open('crypto.key', 'rb').read()
id_table_file = open('id_table.json', 'rb')
ID_TABLE = json.load(id_table_file)
logging.info(ID_TABLE)
JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

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

class LoginHandler (webapp2.RequestHandler):
    def post(self):
        email = self.request.get('email')
        id = convert_email_to_id(email)
        logging.info("id is: " + str(id))
        if id is not None:
            encoded_id = base64.b64encode(aes.encryptData(CRYPTO_KEY, str(id)))
            self.response.set_cookie('SID', encoded_id)
            self.redirect("/")
        else:
            self.response.write(email + " is not a valid e-mail address, please hit back to try again.")

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
    ('/class/(\w+)', ClassHandler)
], debug=True)

