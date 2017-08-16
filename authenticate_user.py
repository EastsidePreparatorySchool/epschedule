import cookielib
import urllib2
import urllib
import logging

AUTHENTICATION_URL = 'https://eastsideprep.instructure.com/login/ldap'

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

def get_auth_token():
    req = urllib2.Request(AUTHENTICATION_URL)
    page = opener.open(req)
    page_source = page.read()
    # Providing start and end bounds below (5000 to 6000 chars) makes our search faster
    # If search ever totally breaks, lower our start bound
    starting_char = page_source.find('authenticity_token" value="', 5000, 6000)

    starting_index = starting_char + 27
    ending_index = starting_char + 27

    while (True):
        ending_index += 1
        if (page_source[ending_index] == '"'):
            return page_source[starting_index : ending_index]

def auth_user(username, password):
    logging.info("Username: " + username)
    # The thing in the UTF8 field is the encoded version of the UTF8 checkmark
    obj = {'authenticity_token' : get_auth_token(), 'pseudonym_session[unique_id]' : username, 'redirect_to_ssl': '1',\
    'pseudonym_session[password]' : password, 'utf8' : '%E2%9C%93', 'pseudonym_session[remember_me]': '0'}

    try:
        res = post(AUTHENTICATION_URL, obj)
        return True
    except urllib2.HTTPError:
        return False