import cookielib
import urllib2
import urllib
import cgi
import string
import os
import sys

AUTHENTICATION_URL = 'https://four11.eastsideprep.org/auth/auth'

cookies = cookielib.LWPCookieJar()
handlers = [
    urllib2.HTTPHandler(),
    urllib2.HTTPSHandler(),
    urllib2.HTTPCookieProcessor(cookies)
    ]
opener = urllib2.build_opener(*handlers)

def post(uri, obj):
    str = urllib.urlencode(obj)
    req = urllib2.Request(uri)
    req.add_data(str)
    return opener.open(req)

def auth_user(username, password):
    obj =  {'user[user_name]' : username, 'user[password]' : password}
    res = post(AUTHENTICATION_URL, obj)
    for cookie in cookies:
        if (cookie.name != "_four11_session"):
            continue
        else:
            if (cookie.value[5] == "0"):
                cookies.clear()
                return True
            else:
                cookies.clear()
                return False
    cookies.clear()
    return False