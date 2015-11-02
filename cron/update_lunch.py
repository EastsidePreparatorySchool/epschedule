import cookielib
import urllib2
import urllib
import cgi
import string
import os
import sys
from icalendar import Calendar, Event
import unicodedata

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    only_ascii = nfkd_form.encode('ASCII', 'ignore')
    return only_ascii

lunches = []

url = "http://www.eastsideprep.org/?plugin=all-in-one-event-calendar&controller=ai1ec_exporter_controller&action=export_events&ai1ec_cat_ids=57?"
req = urllib2.Request(url)
response = urllib2.urlopen(req)
data = response.read()

cal = Calendar.from_ical(data)

for event in cal.walk('vevent'):

    date = event.get('dtstart').dt
    summary = event.get('summary')
    description = remove_accents(event.get('description'))

    obj = { \
        "summary": str(summary), \
        "description": str(description), \
        "day": date.day, \
        "month": date.month, \
        "year": date.year}
    lunches.append(obj)

print lunches
