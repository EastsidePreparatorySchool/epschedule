import cookielib
import urllib2
import urllib
import cgi
import string
import os
import sys
import json

TERM_MAPPING = {"1": "Fall", "2": "Winter", "3": "Spring"}
cookies = cookielib.LWPCookieJar()
handlers = [
    urllib2.HTTPHandler(),
    urllib2.HTTPSHandler(),
    urllib2.HTTPCookieProcessor(cookies)
    ]
opener = urllib2.build_opener(*handlers)

def download(uri, filename, term):
    req = urllib2.Request(uri)
    f = opener.open(req)
    _, params = cgi.parse_header(f.headers.get('Content-Disposition', ''))
    xfilename = params['filename']
    print xfilename

    with open(filename, "wb") as pdf:
	  pdf.write(f.read())

def post(uri, obj):
    str = urllib.urlencode(obj)
    req = urllib2.Request(uri)
    req.add_data(str)
    return opener.open(req)

def dump():
    for cookie in cookies:
        print cookie.name, cookie.value

def download_schedule(student_id, term, year, subdomain):
    url = 'https://' + subdomain + '.eastsideprep.org/registrar/pdf_schedules?color=1&student_id=' + str(student_id) + '&term_id=' + str(term) + '&year_id=' + str(year)
    filename = '../schedules/' + str(student_id) + '-' + str(term) + '-' + year + '.pdf'
    try:
        download(url, filename, term)
        print "Successfully downloaded " + str(student_id)
    except urllib2.HTTPError:
        print "Failed to download " + str(student_id) + ", that number must not be in use"

# Ensure correct use of command prompt

if len(sys.argv) < 3:
    print "Usage: download_schedules.py <username> <password> <term (1-3)> <year (eg. 18)> [subdomain (optional, defaults for four11)]"
    sys.exit()

# Obtain a login cookie

uri = 'https://'
subdomain = 'four11'

if len(sys.argv) >= 6: # If the subdomain argument was specified
    subdomain = sys.argv[5]

uri += subdomain
uri += '.eastsideprep.org/auth/auth'
obj =  {'user[user_name]' : sys.argv[1], 'user[password]' : sys.argv[2]}
term = sys.argv[3]
year = sys.argv[4]
res = post(uri, obj)
dump()

# Download schedules

with open('../data/id_table.json') as data_file:    
    data = json.load(data_file)

for item in data:
    if (term <= 3):
        download_schedule(item["id"], term, year, subdomain)
    else: # If it's 4
        download_schedule(item["id"], 1, year, subdomain)
        download_schedule(item["id"], 2, year, subdomain)
        download_schedule(item["id"], 3, year, subdomain)



print "Schedules downloaded"
print "Parsing schedules"

#import pdf_extract #Runs pdf_extract.py