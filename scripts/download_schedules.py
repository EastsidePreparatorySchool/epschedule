import cookielib
import urllib2
import urllib
import cgi
import string
import os
import sys

TERM_MAPPING = {"1": "Fall", "2": "Winter", "3": "Spring"}
cookies = cookielib.LWPCookieJar()
handlers = [
    urllib2.HTTPHandler(),
    urllib2.HTTPSHandler(),
    urllib2.HTTPCookieProcessor(cookies)
    ]
opener = urllib2.build_opener(*handlers)

def extract_name(filename, term):
    strippedfilename = filename.replace(TERM_MAPPING[term], "")

    # This kid is somehow programmed into the system wrong
    # He won't be able to use the service, but this will fix
    # the parser breaking at his name

    if (strippedfilename == "sch_Kirkpatrick-Heim.pdf"):
        strippedfilename = "sch_Kirkpatrick_Heim.pdf"

    filenamelist = string.split(strippedfilename, '_')
    return filenamelist

def download(uri, filename, term):
    req = urllib2.Request(uri)
    f = opener.open(req)
    _, params = cgi.parse_header(f.headers.get('Content-Disposition', ''))
    xfilename = params['filename']
    print xfilename

    filenamelist = extract_name(xfilename, term)
    finalfilename = '..' + os.sep + 'schedules' + os.sep + filename + '-' + filenamelist[1] + '-' + filenamelist[2] + '.pdf'
    with open(finalfilename, "wb") as pdf:
	  pdf.write(f.read())
    print "done"

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
    filename = str(student_id) + '-' + str(term)
    try:
        download(url, filename, term)
    except urllib2.HTTPError:
        print "Failed to download " + str(student_id) + ", that number must not be in use"

if len(sys.argv) < 3:
    print "Usage: download_schedules.py <username> <password> <term (1-3)> <year (eg. 17)> [subdomain (optional, defaults for four11)]"
    sys.exit()

uri = 'https://'
subdomain = 'four11'
if len(sys.argv) >= 4: # If the subdomain argument was specified
    p = sys.argv[5]

uri += subdomain

uri += '.eastsideprep.org/auth/auth'
obj =  {'user[user_name]' : sys.argv[1], 'user[password]' : sys.argv[2]}
term = sys.argv[3]
year = sys.argv[4]
res = post(uri, obj)
dump()

#for k in range(100, 125) + range(2200, 4700):
for k in range(2504, 4700):
    download_schedule(k, term, year, subdomain)

print "Schedules downloaded"
print "Parsing schedules"

import pdf_extract #Runs pdf_extract.py
import id_table_generator #Runs id_table_generator.py