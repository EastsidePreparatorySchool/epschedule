import cookielib
import urllib2
import urllib
import cgi
import string
import os
import sys
import logging
from icalendar import Calendar, Event
from google.appengine.ext import db
import unicodedata

class Lunch(db.model):
    summary = db.StringProperty(required=True)
    description = db.StringProperty(required=True)
    day = db.DateProperty(required=True)

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    only_ascii = nfkd_form.encode('ASCII', 'ignore')
    return only_ascii

url = "http://www.eastsideprep.org/?plugin=all-in-one-event-calendar&controller=ai1ec_exporter_controller&action=export_events&ai1ec_cat_ids=57?"
req = urllib2.Request(url)
response = urllib2.urlopen(req)
data = response.read()

cal = Calendar.from_ical(data)

for event in cal.walk('vevent'):
    date = event.get('dtstart').dt
    summary = event.get('summary')

    lunches_for_date = db.GqlQuery("SELECT * FROM User WHERE day = :1", date)
    if not lunches_for_date: # If there is already a lunch for that date
        logging.info(summary + " is already in the DB")
        continue

    logging.info("Adding " + summary + " to the DB")
    description = remove_accents(event.get('description'))

    entry = Lunch( \
        summary=str(summary), \
        description=str(description), \
        date=date)
    entry.put()