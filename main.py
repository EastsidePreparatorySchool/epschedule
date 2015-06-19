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
import json
import jinja2
import os
import string
import logging
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
class LoginHandler (webapp2.RequestHandler):
    def post(self):
        email = self.request.get('email')
        id = convert_email_to_id(email)
        logging.info("id is: " + str(id))
        if id is not None:
            self.response.set_cookie('SID', str(id))
            self.redirect("/")
        else:
            self.response.write(email + " is not a valid e-mail address, please hit back to try again.")

class ClassHandler(webapp2.RequestHandler):
    @staticmethod
    def clean_string(text):
        #logging.info("Original text: " + text)
        text = text.lower()
        text = text.replace(".", "")
        text = text.replace("-", "")
        text = text.replace(" ", "_")
        #logging.info("New text: " + text)
        return text
    def get_students(self, name, period):
        file = open('schedules.json', 'rb')
        schedules = json.load(file)
        students_in_class = []
        for schedule in schedules:
            for classinfo in schedule["classes"]:
                logging.info("Is |" + ClassHandler.clean_string(classinfo["name"]) + "| the same as |" + name + "|?")
                logging.info("And, is |" + classinfo["period"].lower() + "| the same as |" + period + "|?")
                if ClassHandler.clean_string(classinfo["name"]) == name and classinfo["period"].lower() == period:
                    logging.info("Yes")
                    students_in_class.append(schedule["firstname"])
                else:
                    logging.info("No")
        return students_in_class
    def get(self, class_id, period):
        #Get the cookie
        id = self.request.cookies.get("SID")
        if id is None:
            self.send_login_response()
            return
        #schedule = self.get_schedule(self.request.get('id'))
        students_in_class = self.get_students(class_id, period)
        self.response.write(students_in_class)
          
class MainHandler(webapp2.RequestHandler):
    #def __init__(self):
    def get_schedule(self, id):
        file = open('schedules.json', 'rb')
        schedules = json.load(file)
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
        id = self.request.cookies.get("SID")
        if id is None:
            self.send_login_response()
            return
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
    ('/class/(\w+)/(\w+)', ClassHandler)
], debug=True)
    