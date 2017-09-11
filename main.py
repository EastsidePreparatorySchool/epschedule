import base64
import copy
import datetime
import jinja2
import json
import logging
import os
import random
import string
import webapp2
from sets import Set

import authenticate_user
import update_lunch

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
GAVIN_ID = "4093"
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
        if (student["username"] == username):
            return student["id"]
    return None

# TODO merge with id to username function
def convert_id_to_email(id):
    email = ""

    if str(id) == DEMO_ID:
        email = DEMO_USER


    for student in ID_TABLE:
        if (str(student["id"]) == str(id)):
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
        if (folder == "school_photos"):
            logging.info("Recieved a request for a full size photo")
        input_data = (lastname + "_" + firstname).lower().replace(" ", "")

        photo_hasher = SHA256.new(CRYPTO_KEY)

        photo_hasher.update(input_data)
        encoded_filename = photo_hasher.hexdigest()

        logging.info(input_data + " --> " + encoded_filename)

        logging.info("Returning the string: '" + '/' + folder + '/' + encoded_filename + '.jpg' + "'")

        return ('/' + folder + '/' + encoded_filename + '.jpg')

    def check_id(self):
        encoded_id = self.request.cookies.get("SID")
        if not encoded_id:
            return None
        # TODO add code to check if id is valid
        id = aes.decryptData(CRYPTO_KEY, base64.b64decode(encoded_id))
        return id

    def check_admin_id(self):
        return self.check_id() == GAVIN_ID

    def query_by_email(self, email, verified = None):
        if verified == True:
          return db.GqlQuery("SELECT * FROM User WHERE email = :1 and verified = TRUE", email)
        elif verified == False:
          return db.GqlQuery("SELECT * FROM User WHERE email = :1 and verified = FALSE", email)
        else:
          return db.GqlQuery("SELECT * FROM User WHERE email = :1", email)

    # Returns false if there is already a registered user, or true if not
    def check_no_account(self, email):
        user_obj_query = self.query_by_email(email, True)
        if user_obj_query.get():
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
            if schedule["sid"] == int(id): # If the schedule is the user's schedule
                return schedule
        return None

    def get_components_filename(self):
        return 'components.html'
        
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
            if int(schedule['sid']) == int(id):
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

class LoginHandler (BaseHandler):
    def post(self):
        logging.info("Running handler")
        email = self.request.get('email').lower()
        password = self.request.get('password')

        id = convert_email_to_id(email)
        logging.info(str(id))

        if not id: # If there is no id for the email, don't try to log in
            self.response.write(json.dumps({"error":"That email is not recognized."}))
            return

        username = string.split(email, "@")[0]


        logging.info("Calling auth user with args " + username + ", " + password)

        if not (authenticate_user.auth_user(username + "@eastsideprep.org", password)): # If four11 authentication failed, return our error
            self.response.write(json.dumps({"error":"Your password is incorrect."}))
            return


        # If authentication was successful, check to see if the person has an EPSchedule account
        user_obj_query = self.query_by_email(email, True)
        if not user_obj_query.get():
            student_obj = User(email = username + "@eastsideprep.org", verified = True, join_date = datetime.datetime.now())
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

class LogoutHandler(BaseHandler):
    def post(self):
        self.response.delete_cookie("SID")
        self.response.delete_cookie("SEENPRIVDIALOG")
        self.response.write(json.dumps({}))

class ClassHandler(BaseHandler):
    def gen_opted_in_table(self):
        table = set()
        opted_in = db.GqlQuery("SELECT * FROM User WHERE share_photo = TRUE")
        for student in opted_in:
            table.add(student.email)

        return table

    def get_teacher_photo(self, num):
        for schedule in get_schedule_data():
            if is_teacher_schedule(schedule): # If they are a teacher
                num -= 1
                if num <= 0:
                    logging.info("Returning schedule, firstname is: " + schedule['firstname'])
                    return schedule

    def get_class_schedule(self, class_name, period):
        schedules = get_schedule_data()
        logging.info("Finished retrieving schedule data")
        result = None
        logging.info("Starting DB query")
        opted_in = self.gen_opted_in_table()
        logging.info("Finished DB query")

        for schedule in schedules: # Load up each student's schedule
            for classobj in schedule['classes']: # For each one of their classes
                if normalize_classname(classobj['name']) == class_name.lower() and \
                    classobj['period'].lower() == period.lower(): # Check class name and period match
                    if classobj['teacher'] or classobj['name'] == "Free Period": # If they are a student or it is a free period
                        if not result:
                            result = {"period": classobj['period'], \
                                      "teacher": classobj['teacher'], \
                                      "students": []}

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
        logging.info("Finishing schedule iteration")

        if result:
            result['students'].sort(key=lambda s: s['firstname'])
        logging.info("Finished handling request")
        return result
    def get(self, class_name, period):
        logging.info("Class schedule retrival started")
        # Get the cookie
        id = self.check_id()
        if id is None:
            self.error(403)
            return

        # schedule = self.get_schedule(self.request.get('id'))
        result = self.get_class_schedule(class_name, period)
        if not result:
            self.error(404)
            return

        self.response.write(json.dumps(result))
        logging.info("Class schedule retrival finished")


class StudentHandler(BaseHandler):
    def get(self, student_name):
        id = self.check_id()
        if id is None:
            self.error(403)
            return

        if id == str(DEMO_ID):
            id = GAVIN_ID

        # Split student_name into firstname and lastname
        student_names = student_name.split("_")
        firstname = student_names[0].lower()
        lastname = student_names[1].lower()

        show_full_schedule = False
        show_photo = False
        email = generate_email(firstname, lastname)
        logging.info(email)
        user_obj_query = self.query_by_email(email, True)
        user_obj = user_obj_query.get()

        if user_obj:
            logging.info("Found user obj")
            show_full_schedule = user_obj.share_schedule
            show_photo = user_obj.share_photo
            logging.info("show_photo equals " + str(show_photo))

        student_schedule = self.get_schedule_for_name(firstname, lastname)
        logging.info(student_schedule)

        if not student_schedule:
            self.error(404)
            return

        user_schedule = self.get_schedule_for_id(id)
        logging.info(user_schedule)

        if is_teacher_schedule(user_schedule) or show_full_schedule:
            # If the user is a teacher
            response_schedule = copy.deepcopy(student_schedule)
        else:
            response_schedule = self.sanitize_schedule(student_schedule, user_schedule)

        # Generate email address
        response_schedule["email"] = email

        if show_photo:
            logging.info("IF statement has found show photo to be true")
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
        dataobj = {'classes': []}
        altperiods = Set()
        freerooms = Set()

        if id == DEMO_ID: # If this is the demo account
            id = GAVIN_ID
        schedule_data = get_schedule_data()
        user_schedule = None
        user_class = None

        period = period.upper()

        # Get user's schedule
        for schedule in schedule_data:
            if schedule['sid'] == int(id):
                user_schedule = schedule
                break

        for class_obj in user_schedule['classes']: # Find out which class the user has then
            if class_obj['period'] == period:
                user_class = class_obj
                break

        for schedule in schedule_data:
            logging.info("User's grade is " + str(user_schedule['grade']) + ", test grade is " + str(schedule['grade']))
            if schedule['grade'] == user_schedule['grade']:
                logging.info("They're a match!")
                # For each person in the user's grade:

                # Get what class they have in the period in question
                testclass = {}
                for clss in schedule['classes']:
                    if clss['period'] == period and clss['name'] != "Free Period":
                        testclass = clss
                        break

                if testclass:
                    # Test if we already have an appropriate object
                    newobjectneeded = True

                    for clss in dataobj['classes']:
                        if clss['name'] == testclass['name'] and clss['period'] == testclass['period']:
                            newobjectneeded = False
                            break

                    if newobjectneeded:
                        if not user_schedule['grade']:
                            testclass = copy.copy(testclass)
                            testclass['teacher'] = schedule['firstname'] + " " + schedule['lastname']

                        dataobj['classes'].append(testclass)


                        dataobj['classes'][-1]['students'] = 0

            for class_obj in schedule['classes']:

                # For each class, add its room to our room set
                freerooms.add(class_obj['room'])

                # For each class, if it's the same class that
                # we have that period but in a different period,
                # add that to "other periods" list
                if class_obj['name'] == user_class['name']:
                    altperiods.add(class_obj['period'])

        for schedule in schedule_data: # Find out which rooms are free
            if not schedule['grade']:
                continue
            for clss in schedule['classes']:
                if clss['period'] == period:
                    for test_class in dataobj['classes']:
                        if normalize_classname(test_class['name']) == normalize_classname(clss['name']):
                            test_class['students'] += 1

                    freerooms.discard(clss['room'])

        # List comprehension to remove duplicate classes
        # While it would also be possible to do this with a for loop,
        # the fastest way is list comprehension
        dataobj['classes'] = \
        map(dict, set(tuple(sorted(potclass.items())) for potclass in dataobj['classes']))

        for clss in reversed(dataobj['classes']):
            if not clss['room']:
                dataobj['classes'].remove(clss)


        for clss in dataobj['classes']:
            # We already know periods are the same
            logging.info("Testing " + json.dumps(clss))
            logging.info("Does it have different information then " + json.dumps(user_class))
            if clss['name'] == user_class['name'] and clss['room'] == user_class['room']:
                logging.info("No!")
                dataobj['currentclass'] = clss
                dataobj['classes'].remove(clss)
                break
        
        if 'currentclass' not in dataobj:
            dataobj['currentclass'] = {'name': "Free Period", 'period': period, 'room': None, 'teacher': None}

        altperiods.remove(user_class['period'])

        dataobj['period'] = period
        dataobj['freerooms'] = sorted(list(freerooms))
        dataobj['classes'].sort(key=lambda x: x['name'])
        dataobj['altperiods'] = sorted(list(altperiods))

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

        if len(room_schedule['classes']) == 0:
            self.error(404)
            return

        self.response.write(json.dumps(room_schedule))

class TeacherHandler(BaseHandler):
    def get(self, teacher):
        id = self.check_id()
        if id is None:
            self.error(403)
            return

        teacher = teacher.lower()
        bio = self.get_bio(teacher)
        schedule_data = get_schedule_data()
        teachernames = string.split(teacher, "_")
        result = None

        for schedule in schedule_data:
            if schedule['firstname'].lower() == teachernames[0] and schedule['lastname'].lower() == teachernames[1]:
                result = copy.deepcopy(schedule)
                result['email'] = generate_email(schedule['firstname'], schedule['lastname'])
                result['bio'] = bio

        if not result:
            self.error(404)
            return

        self.response.write(json.dumps(result))

    def get_bio(self, teacher):
        for bio in BIOS:
            if bio['name'] == teacher:
                return bio['bio']

class MainHandler(BaseHandler):
    # def __init__(self):
    def get_schedule(self, id):
        schedules = get_schedule_data()
        for schedule in schedules:
            if schedule['sid'] == int(id):
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
            id = GAVIN_ID
        # schedule = self.get_schedule(self.request.get('id'))
        schedule = self.get_schedule(id)
        lunch_objs = update_lunch.getLunchForDate(datetime.date.today())

        if schedule is not None:

            show_privacy_dialog = False

            if self.request.cookies.get("SEENPRIVDIALOG") != "1":
                if schedule['grade']: # If the user is a student
                    user_obj_query = self.query_by_email(convert_id_to_email(id), True)
                    obj = user_obj_query.get()
                    if obj:
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
        if not self.check_admin_id():
            self.error(403)
            return

        data = self.read_db()

        html = "<h1>Stats</h1>"

        html += "<h2>" + str(len(data))
        html += " unique emails entered</h2>"

        only_verified_dict = {k: v for (k, v) in data.iteritems() \
            if len(v['verified']) == 1 and len(v['unverified']) == 0 }
        only_verified_list = sorted([k for k in only_verified_dict])
        num_four11 = len({k: v for (k, v) in only_verified_dict.iteritems() \
            if not v.get('password')})
        num_seen_dialog = len({k: v for (k, v) in only_verified_dict.iteritems() \
            if v.get('seen_update_dialog')})
        num_share_photo = len({k: v for (k, v) in only_verified_dict.iteritems() \
            if v.get('share_photo')})
        num_share_schedule = len({k: v for (k, v) in only_verified_dict.iteritems() \
            if v.get('share_schedule')})
        percent_four11 = 0
        percent_seen_dialog = 0
        percent_share_photo = 0
        percent_share_schedule = 0
        if len(only_verified_list) > 0:
            percent_four11 = num_four11 * 100 / len(only_verified_list)
            percent_seen_dialog = num_seen_dialog * 100 / len(only_verified_list)
        if num_seen_dialog > 0:
            percent_share_photo = num_share_photo * 100 / num_seen_dialog
            percent_share_schedule = num_share_schedule * 100 / num_seen_dialog

        html += "<h3>" + str(len(only_verified_list)) + " emails in good condition</h3>"
        for email in only_verified_list:
            html += email + "<br>"
        html += "<h4>" + str(num_four11) + \
            " (" + str(percent_four11) + "%) using four11 login<br>"
        html += str(num_seen_dialog) + \
            " (" + str(percent_seen_dialog) + "%) have seen privacy dialog<br>"
        html += str(num_share_photo) + \
            " (" + str(percent_share_photo) + "%) sharing their photo<br>"
        html += str(num_share_schedule) + \
            " (" + str(percent_share_schedule) + "%) sharing their schedule</h4>"

        verified_and_unverified = sorted([ k for k, v in data.iteritems() \
            if len(v['verified']) >= 1 and len(v['unverified']) >= 1 ])
        html += "<h3>" + str(len(verified_and_unverified)) + " emails with verified and unverified records</h3>"
        for email in verified_and_unverified:
            html += email + " [" + str(len(data[email]['unverified'])) + "]<br>"

        comment = """only_unverified = sorted([ k for k, v in data.iteritems() \
            if len(v['verified']) == 0 and len(v['unverified']) >= 1 ])

        html += "<h3>" + str(len(only_unverified)) + " emails with only unverified records</h3>"
        for email in only_unverified:
            email_schedule = self.get_schedule_for_id(convert_email_to_id(email))
            is_valid = "invalid" # Will either be "valid" or "invalid"

            if email_schedule:
                is_valid = "valid"

            html += email + " [" + str(len(data[email]['unverified'])) + ", " + is_valid + ']<br>'"""

        multiple_verified = sorted([ k for k, v in data.iteritems() \
            if len(v['verified']) > 1 ])
        # If there are ever any entries in multiple_verified, the DB is in a very bad state
        if multiple_verified:
            html += "<h3>Attention! There are " + str(len(multiple_verified)) + " emails with more than one verified record. The DB is REALLY messed up!</h3>"
            for email in multiple_verified:
                html += email + " [" + str(len(data[email]['verified'])) + ", " + str(len(data[email]['unverified'])) + "]<br>"

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
        self.response.write(html)

    # Returns the entire database as a dictionary
    def read_db(self):
        data = {}
        query = db.GqlQuery("SELECT * FROM User")
        for query_result in query:
            if not query_result.email in data:
                data[query_result.email] = {'verified': [], 'unverified': []}
            # Append the entity's key to the appropriate list
            obj =  data[query_result.email]
            obj[self.get_key(query_result.verified)].append(query_result.key())
            # If we have a verified record, add the privacy info
            if query_result.verified:
                obj['password'] = query_result.password
                if query_result.seen_update_dialog:
                    obj['seen_update_dialog'] = True
                if query_result.share_photo:
                    obj['share_photo'] = True
                if query_result.share_schedule:
                    obj['share_schedule'] = True

        return data

    # A function that takes either True or False and returns either "verified" or "unverified"
    def get_key(self, verified):
        if verified:
            return "verified"
        return "unverified"

    def post(self, action):
        if not self.check_admin_id():
            self.error(403)
            return

        if action == "emailblast":
            self.send_email_blast()
        elif action == "cleanup":
            self.clean_up_db()
        elif action == "emaildomainadd":
            self.email_domain_add()

    def send_email_blast(self):
        data = self.read_db()
        # Generate unverified_row_ids

        for email in data:
            if len(data[email]['verified']) == 0:
                numerical_id = data[email]['unverified'][0].id()
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
        data = self.read_db()
        for email in data:
            if len(data[email]['verified']) == 1 and len(data[email]['unverified']) >= 1:
                db.delete(data[email]['unverified'])

    def email_domain_add(self):
        query = db.GqlQuery("SELECT * FROM User")
        for query_result in query:
            if "@eastsideprep.org" not in query_result.email:
                query_result.email += "@eastsideprep.org"
                query_result.put()

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
        user_obj_query = self.query_by_email(email, True)
        return user_obj_query.get()

    def string_to_boolean(self, string):
        if string == 'true':
            return True
        elif string == 'false':
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

        user_obj.share_photo = self.string_to_boolean(self.request.get('share_photo'))
        user_obj.share_schedule = self.string_to_boolean(self.request.get('share_schedule'))
        user_obj.seen_update_dialog = True;
        user_obj.put()
        self.response.write(json.dumps({}))

class AvatarHandler(BaseHandler):
    def get(self, user):
        if not self.check_admin_id():
            self.error(403)
            return
        logging.info("Recieved an administrator get request")
        args = string.split(user, '_')
        url = self.gen_photo_url(args[1], args[0], 'school_photos')
        self.redirect(url)

class DynamicElementHandler(BaseHandler):
    def get(self, component):
        template_values = {}

        if self.request.get('behavior'):
            template_values['behaviors'] = self.request.get('behavior')

        if self.request.get('name'):
            template_values['name'] = self.request.get('name')
        else:
            template_values['name'] = string.split(component, ".")

        template = JINJA_ENVIRONMENT.get_template('dynamic/' + component)
        self.response.write(template.render(template_values))

class SearchHandler(BaseHandler):
    def get_url_prefix(self, grade):
        if grade:
            return "student"
        else:
            return "teacher"

    def get(self, keyword):
        results = []
        for schedule in SCHEDULE_INFO:
            test_keyword = schedule['firstname'] + " " + schedule['lastname']
            if keyword.lower() in test_keyword.lower():
                results.append({"name": test_keyword, "prefix": self.get_url_prefix(schedule['grade'])})
                if (len(results) >= 5): # We only display five results
                    break

        self.response.write(json.dumps(results))


app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/about', AboutHandler),
    ('/avatar/(\w+).jpg', AvatarHandler),
    ('/dynamic/(.*)', DynamicElementHandler),
    ('/login', LoginHandler),
    ('/logout', LogoutHandler),
    ('/privacy', PrivacyHandler),
    ('/class/([\w\-]+)/([\w\-]+)', ClassHandler),
    ('/period/(\w+)', PeriodHandler),
    ('/room/([\w\-]+)', RoomHandler),
    ('/teacher/([\w\-]+)', TeacherHandler),
    ('/student/([\w\-]+)', StudentHandler),
    ('/lunch', LunchRateHandler),
    ('/admin', AdminHandler),
    ('/admin/(\w+)', AdminHandler),
    ('/search/(.*)', SearchHandler),
    ('/cron/(\w+)', CronHandler),
], debug=True)