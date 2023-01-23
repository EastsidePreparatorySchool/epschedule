import datetime
import logging
import os

import requests
from google.cloud import ndb

# TODO(juberti): Fully mock out NDB so we don't need to talk to GCP when running tests.
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service_account.json"

# Globals
TIME_FORMAT = "%Y%m%dT%H%M%S"
LUNCH_URL = "http://www.eastsideprep.org/wp-content/plugins/dpProEventCalendar/includes/ical.php?calendar_id=19"

# NDB class definitions
class Lunch(ndb.Model):
    summary = ndb.StringProperty(required=True)
    # description is a list of lines in the description
    description = ndb.StringProperty(repeated=True)
    day = ndb.DateProperty(required=True)

    @classmethod
    def query_with_time_constraint(cls, earliest_lunch):
        return cls.query().filter(Lunch.day >= earliest_lunch)


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
                colon_separated_values = line.split(":", 1)
                # this ends up with [DTSTART;TZID=America/Los_Angeles, 20151030T110500]

                # Garbage anything between ; and :
                last_prop_name = colon_separated_values[0].split(";")[0]
                # this ends up with DTSTART

                # equivalent with properties[DTSTART] = 20151030T110500 and places within the dict
                properties[last_prop_name] = colon_separated_values[1]
    return events


# Sanitizes a list of events obtained from parse_events
def save_events(events, dry_run=False, verbose=False):
    client = ndb.Client()
    for event in events:
        # Convert the datetime string (e.g. 20151124T233401) to a date object
        # Gets format from global var
        try:
            date = datetime.datetime.strptime(event["DTSTART"], TIME_FORMAT).date()
        except ValueError:
            date = datetime.datetime.strptime(event["DTSTART"], "%Y%m%d").date()

        summary = event["SUMMARY"]

        # Remove formatting from the description, and break it up into lines
        desc = event["DESCRIPTION"]
        start = desc.find("[text_output]")
        end = desc.find("[/text_output]")
        desc = desc[start + 13 : end]

        # To keep things brief, we'll cap the length at two lines
        lines = desc.split("\\n")[:2]
        # Strip out any extra whitespace
        description = [line.strip() for line in lines]

        print(f"{date}: {summary}")
        if verbose:
            for line in description:
                print("           ", line)
        if not dry_run:
            entry = Lunch(summary=summary, description=description, day=date)
            write_event_to_db(client, entry)


def write_event_to_db(client, entry):  # Places a single entry into the db
    # this enables using NDB
    with client.context():
        # Check how many lunches there are already for that date (always 1 or 0)
        lunches_for_date = Lunch.query(Lunch.day == entry.day)

        # Check if there is already a lunch for that date (it has already been parsed)
        for lunch in lunches_for_date:
            logging.info(str(entry.day) + " is already in the DB")
            lunch.key.delete()  # Delete the existing ndb entity

        # If not, log it and put it into the db
        logging.info(f"Adding lunch entry to DB: {str(entry)}")
        entry.put()


def add_events(response_text, dry_run=False, verbose=False):
    text = response_text
    lines = text.splitlines()
    events = parse_events(lines)

    # Sanitize and write the events to the database
    save_events(events, dry_run, verbose)


# ---------------------------------------------- #
# Functions below here will be called externally #
# ---------------------------------------------- #


def read_lunches(dry_run=False, verbose=False):  # Update the database with new lunches
    response = requests.get(LUNCH_URL)
    add_events(response.text, dry_run, verbose)


# Returns lunches to be displayed in a schedule
def get_lunches_since_date(date):
    client = ndb.Client()
    with client.context():
        # days_into_past is the number of days into the past to go
        earliest_lunch = date
        lunch_objs = []
        for lunch_obj in Lunch.query_with_time_constraint(earliest_lunch):
            cleaned_description = (
                []
            )  # the desc after it is cleaned of escape characters and new lines
            for description_section in lunch_obj.description:
                if not (
                    description_section == ""
                    or description_section == " "
                    or description_section == False
                ):  # eliminates a section if it is empty or just a space
                    cleaned_description.append(
                        description_section.replace("\\,", ",")
                        .replace("\n", "")
                        .replace("&amp\\;", "&")
                        .replace(
                            "Click here for meal account and food services details", ""
                        )
                    )
            # this for loop destroyed all escape characters and new lines in the description

            obj = {
                "summary": lunch_obj.summary.replace(
                    "\\,", ","
                ),  # deletes all annoying escape character backslashes
                "description": cleaned_description,
                "day": lunch_obj.day.day,
                "month": lunch_obj.day.month,
                "year": lunch_obj.day.year,
            }
            lunch_objs.append(obj)

    return lunch_objs
