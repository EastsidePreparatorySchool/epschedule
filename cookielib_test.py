import cookielib
import urllib2
import urllib
import cgi
import string
import os
import sys

cookies = cookielib.LWPCookieJar()
handlers = [
    urllib2.HTTPHandler(),
    urllib2.HTTPSHandler(),
    urllib2.HTTPCookieProcessor(cookies)
    ]
opener = urllib2.build_opener(*handlers)

def extract_name(filename):
    filenamelist = string.split(filename, '_')
    print filenamelist[1]
    return filenamelist

def download(uri, filename):
    print uri
    req = urllib2.Request(uri)
    f = opener.open(req)
    _, params = cgi.parse_header(f.headers.get('Content-Disposition', ''))
    xfilename = params['filename']
    filenamelist = extract_name(xfilename)
    finalfilename = 'schedules' + os.sep + filename + '-' + filenamelist[1] + '-' + filenamelist[2] + '.pdf'
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
		
def download_schedule(student_id, term):
    url = 'https://four11.eastsideprep.org/registrar/pdf_schedules?color=1&student_id=' + str(student_id) + '&term_id=' + str(term) + '&year_id=15'
    filename = str(student_id) + '-' + str(term)
    download(url, filename)

uri = 'https://four11.eastsideprep.org/auth/auth'
if len(sys.argv) < 3:
    print "Usage: cookielib_test.py <username> <password>"
    sys.exit()
obj =  {'user[user_name]' : sys.argv[1], 'user[password]' : sys.argv[2]}
res = post(uri, obj)
dump()

#('https://four11.eastsideprep.org/registrar/pdf_schedules?color=1&student_id=4093&term_id=3&year_id=15')
download_schedule(4093, 3)
download_schedule(4268, 3)