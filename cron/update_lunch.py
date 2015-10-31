import cookielib
import urllib2
import urllib
import cgi
import string
import os
import sys
from google.appengine.ext import db

url = "http://www.eastsideprep.org/?plugin=all-in-one-event-calendar&controller=ai1ec_exporter_controller&action=export_events&ai1ec_cat_ids=57?"