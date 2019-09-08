import datetime
import logging
import re
import string
import urllib2
from HTMLParser import HTMLParser

from google.appengine.ext import ndb

# Globals
format = "%Y%m%dT%H%M%S"
lunch_url = "http://www.eastsideprep.org/wp-content/plugins/dpProEventCalendar/includes/ical.php?calendar_id=19"

# NDB class definitions

class Lunch(ndb.Model):
    summary = ndb.StringProperty(required=True)
    # description is a list of lines in the description
    description = ndb.StringProperty(repeated=True)
    day = ndb.DateProperty(required=True)


class LunchRating(ndb.Model):
    sid = ndb.IntegerProperty(required=True)
    rating = ndb.IntegerProperty(required=True)  # 1-10 star rating
    lunch_id = ndb.IntegerProperty(required=True)  # Which type of lunch its for
    created = ndb.DateProperty()  # What date the rating was made


# Functions for parsing iCal files


def parse_events(lines):  # lines is a list of all lines of text in the whole file 
    in_event = False  # Whether the current line is in an event
    properties = {}  # When properties are discovered, they will be stuffed in here
    events = []  # The list of all properties objects
    last_prop_name = None
    for line in lines:
        if line == "BEGIN:VEVENT":
            in_event = True
        elif line == "END:VEVENT":
            in_event = False
            events.append(properties)
            properties = {}
        elif in_event:
            if (
                line[0] == " "
            ):  # If the current line is a continuation of the previous line
                properties[last_prop_name] += line[1:]
            else:  # If it is the start of a normal line
                # Sample line: DTSTART;TZID=America/Los_Angeles:20151030T110500
                colon_separated_values = string.split(line, ":", 1)

                # Garbage anything between ; and :
                last_prop_name = string.split(colon_separated_values[0], ";")[0]

                properties[last_prop_name] = colon_separated_values[1]
    return events


def sanitize_events(events):  # Sanitizes a list of events obtained from parse_events
    for event in events:
        # Convert the datetime string (e.g. 20151124T233401) to a date object
        # Gets format from global var
        try:
            date = datetime.datetime.strptime(event["DTSTART"], format).date()
        except ValueError:
            date = datetime.datetime.strptime(event["DTSTART"], "%Y%m%d").date()

        # Remove the price and back slashes from the summary
        summary = string.split(event["SUMMARY"], " | ")[1]  # Remove the price
        summary = summary.replace("\\", "")  # Remove back slashes
        summary = summary.replace("&amp;", "&") #Write ampersands correctly

        # Remove html from the description, and break it up into lines
        desc = event["DESCRIPTION"]
        desc = desc.replace("\,", ",")
        desc = desc.replace("\;", ";")
        desc = desc.replace("\\r", ";")
        desc = desc.replace("&amp;", "&")

        no_html_desc = re.sub("<.*?>", "", desc)
        description = string.split(no_html_desc, "\\n")

        # print("                                     ")
        # print(summary)
        # print(description)
        print("I'm being run!")
        entry = Lunch(summary=summary, description=description, day=date)

        write_event_to_db(entry)


def write_event_to_db(entry):  # Places a single entry into the db

    # Check how many lunches there are already for that date (always 1 or 0)
    lunches_for_date = Lunch.query(Lunch.day == entry.day)

    # Check if there is already a lunch for that date (it has already been parsed)
    has_lunch_for_date = False
    for lunch in lunches_for_date:
        has_lunch_for_date = True
        break

    # If it has been parsed
    if has_lunch_for_date:
        logging.info(str(entry.day) + " is already in the DB")
        return

    # If not, log it and put it into the db

    logging.info(str(entry))
    entry.put()


def add_events(response):
    text = response.read()
    lines = text.splitlines()
    events = parse_events(lines)

    # Sanitize and write the events to the database
    sanitize_events(events)


# ---------------------------------------------- #
# Functions below here will be called externally #
# ---------------------------------------------- #


def test_read_lunches(fakepath):  # Will be called by unit tests
    # Adds two fake lunch objects to db with dates 12/20/9999 and 12/21/9999
    mainresponse = open(fakepath)
    add_events(mainresponse)


def read_lunches():  # Update the database with new lunches
    # lunch_url is a global var
    mainresponse = urllib2.urlopen(lunch_url)
    add_events(mainresponse)


# Returns lunches to be displayed in a schedule
def getLunchForDate(current_date, days_into_past=28):
    # days_into_past is the number of days into the past to go
    earliest_lunch = current_date - datetime.timedelta(days_into_past)
    query = Lunch.query(Lunch.day >= earliest_lunch)
    lunch_objs = []
    for lunch_obj in query:
        obj = {
            "summary": lunch_obj.summary,
            "description": lunch_obj.description,
            "day": lunch_obj.day.day,
            "month": lunch_obj.day.month,
            "year": lunch_obj.day.year,
        }
        lunch_objs.append(obj)
    return lunch_objs


def calc_lunch_rating(lunch_id):  # Uses mean, returns a float
    rating_sum = 0
    rating_num = 0

    lunches = LunchRating.query(LunchRating.lunch_id == lunch_id)
    for lunch in lunches:
        rating_sum += lunch.rating
        rating_num += 1

    return rating_sum / float(rating_num)


def get_lunch_id_for_date(date):
    lunches = Lunch.query(Lunch.day == date).fetch(1)
    if lunches:  # If there is a lunch for the date
        return lunches[0].key.id()
    else:
        return None


def get_all_future_lunches(date):
    lunches = Lunch.query(Lunch.day >= date).order(Lunch.day).fetch(5)
    obj = []
    for item in lunches:
        obj.append({"day": str(item.day), "summary": item.summary})
    return obj


def place_rating(rating, sid, lunch_id, date, overwrite=True):
    # Detects if there is already a rating for that student and lunch,
    # and if not (or if overwrite is true) writes a new rating
    # Returns whether a rating was overwritten

    overwrote = False

    current_rating = LunchRating.query(
        LunchRating.sid == sid and LunchRating.lunch_id == lunch_id
    )

    for foo in current_rating:  # If there is already a rating
        if not overwrite:  # If not set to overwrite
            return overwrote  # To not make any changes

        # Otherwise, if we should overwrite,
        foo.key.delete()  # Delete the existing ndb entity
        overwrote = True  # Record that something was overwritten

    # Place a new rating
    obj = LunchRating(sid=sid, rating=rating, lunch_id=lunch_id, created=date)
    obj.put()

    return overwrote

#read_lunches()