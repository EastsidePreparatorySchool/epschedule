import urllib2
import urllib
import string
import string
import logging
import datetime
import re
from google.appengine.ext import ndb
from HTMLParser import HTMLParser

class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

class Lunch(ndb.Model):
    summary = ndb.StringProperty(required=True)
    # description is a list of lines in the description
    description = ndb.StringProperty(repeated=True)
    day = ndb.DateProperty(required=True)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

def getDateObj(text):
    pass

def getEvents(lines): # lines is a list of all lines of text in the whole file
    in_event = False # Whether the current line is in an event
    properties = {} # When properties are discovered, they will be stuffed in here
    events = [] # The list of all properties objects
    last_prop_name = None
    for line in lines:
        if line == "BEGIN:VEVENT":
            in_event = True
        elif line == "END:VEVENT":
            in_event = False
            events.append(properties)
            properties = {}
        elif in_event:
            print line
            if line[0] == " ": # If the current line is a continuation of the previous line
                properties[last_prop_name] += line[1:]
            else: # If it is the start of a normal line
                # Sample line: DTSTART;TZID=America/Los_Angeles:20151030T110500
                colon_seperated_values = string.split(line, ":")

                # Garbage anything between ; and :
                last_prop_name = string.split(colon_seperated_values[0], ";")[0]

                properties[last_prop_name] = colon_seperated_values[1]
    return events

def writeToDB(events): # Takes the raw events, sanitizes them, and plops them into the db
    for event in events:
        # Prettify the summary, date, and description

        # Convert the datetime string (e.g. 20151124T233401) to a date object
        format = "%Y%m%dT%H%M%S"
        date = datetime.datetime.strptime(event["DTSTART"], format).date()

        lunches_for_date = Lunch.query(Lunch.day == date)
        logging.info(lunches_for_date)
        has_lunch_for_date = False

        for lunch in lunches_for_date: # If any results were returned
            has_lunch_for_date = True

        if (has_lunch_for_date):
            logging.info(str(date) + " is already in the DB")
            continue

        # Remove the price and back slashes from the summary
        summary = string.split(event["SUMMARY"], " | ")[0] # Remove the price
        summary = summary.replace("\\", "") # Remove back slashes

        # Remove html from the description, and break it up into lines
        desc = event["DESCRIPTION"]
        desc = desc.replace("\,", ",")
        desc = desc.replace("\;", ";")
        no_html_desc = re.sub("<.*?>", '', desc)
        description = string.split(no_html_desc, '\\n')

        entry = Lunch( \
            summary=summary, \
            description=description, \
            day=date)
        logging.info(str(entry))
        entry.put()

def updateDB():
    url = "http://www.eastsideprep.org/?plugin=all-in-one-event-calendar&controller=ai1ec_exporter_controller&action=export_events&ai1ec_cat_ids=57?"
    mainresponse = urllib2.urlopen(url)
    #mainresponse = open("download.ics") # Opens downloaded ics file

    text = mainresponse.read()
    lines = text.splitlines()
    events = getEvents(lines)
    writeToDB(events)

def getLunchForDate(days_into_past=7): # date is a date object
    # days_into_past is the number of days into the past to go
    current_date = datetime.date.today()
    #current_date = datetime.date(2015, 10, 27)
    earliest_lunch = current_date - datetime.timedelta(days_into_past)
    query = Lunch.query(Lunch.day >= earliest_lunch)
    lunch_objs = []
    for lunch_obj in query:
        obj = { \
            "summary": lunch_obj.summary, \
            "description": lunch_obj.description, \
            "day": lunch_obj.day.day, \
            "month": lunch_obj.day.month, \
            "year": lunch_obj.day.year \
        }
        lunch_objs.append(obj)
    return lunch_objs
