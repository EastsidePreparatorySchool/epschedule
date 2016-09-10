import datetime
import json
import os
import unittest
import webtest

# Hack to force the app to load test data.
os.environ['EPSCHEDULE_USE_TEST_DATA'] = '1'
import main  # module being tested
from main import User
import update_lunch

from google.appengine.api import datastore
from google.appengine.ext import db
from google.appengine.ext import testbed
from google.appengine.ext import vendor

vendor.add('lib')

from py_bcrypt import bcrypt

TEST_EMAIL = 'tturtle@eastsideprep.org'
ADMIN_EMAIL = 'suzwack@eastsideprep.org'
NON_EPS_EMAIL = 'test@example.org'
UNKNOWN_EPS_EMAIL = 'unknown@eastsideprep.org'
INVALID_EPS_EMAIL = 'invalid@eastsideprep.org'
TEST_PASSWORD = 'testtest'
ADMIN_PASSWORD = 'adminpass'
BAD_PASSWORD = 'badbadbad'
TEST_LUNCH_PATH = 'data/test_lunch.ics'
TEST_LUNCH_DATE = datetime.date(9999, 12, 20)
TEST_LUNCH_SUMMARY = 'Foobar'
LUNCH_DESCRIPTION_LENGTH = 3

class FakeSendGridClient():
    def __init__(self):
        self.emails = []
    def send(self, email):
        self.emails.append(email)

class HandlerTestBase(unittest.TestCase):
    def setUp(self):
        # Test setup boilerplate.
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.test_app = webtest.TestApp(main.app)
        self.fake_sendgrid = FakeSendGridClient()
        main.SendGridClient.send = self.fake_sendgrid.send

    def tearDown(self):
        self.testbed.deactivate()

    def login(self):
        return self.sendEmailPasswordPostRequest('/login', TEST_EMAIL, TEST_PASSWORD)

    def loginAsAdmin(self):
        return self.sendEmailPasswordPostRequest('/login', ADMIN_EMAIL, ADMIN_PASSWORD)

    def sendGetRequest(self, path, status=200):
        # PhantomJS uses WebKit, so Safari is closest to the truth.
        return self.test_app.get(path, headers = {'User-Agent': 'Safari'},
                                 status=status)

    def sendEmailPasswordPostRequest(self, path, email, password):
        body = 'email={0}&password={1}'.format(email, password)
        return self.test_app.post(path, body, headers = {'User-Agent': 'Safari'})

    def sendPostRequest(self, path, body=None):
        if not body:
          return self.test_app.post(path)
        return self.test_app.post(path, body)


    def assertNoError(self, response):
        obj = json.loads(response.body)
        self.assertEqual(obj['error'], '')

    def assertHasError(self, response):
        obj = json.loads(response.body)
        self.assertNotEqual(obj['error'], '')

    def addVerifiedUser(self):
        self.addUser(TEST_EMAIL, TEST_PASSWORD, datetime.datetime.now(), True)

    def addUnverifiedUser(self):
        self.addUser(TEST_EMAIL, TEST_PASSWORD, datetime.datetime.now(), False)

    def addAdminUser(self):
        self.addUser(ADMIN_EMAIL, ADMIN_PASSWORD, datetime.datetime.now(), True)

    def addUser(self, email, password, join_date, verified):
        hashed = bcrypt.hashpw(password, bcrypt.gensalt(1))
        user = User(email = email,
                    password = hashed,
                    join_date = join_date,
                    verified = verified)
        user.put()

    def queryUsersByEmail(self, email):
        users = []
        query = db.GqlQuery("SELECT * FROM User WHERE email = :1", email)
        for result in query:
            users.append(result)
        return users

    def getSentEmails(self):
        return self.fake_sendgrid.emails

    def getPathFromEmail(self, email):
        body = email.html
        href = body.find('href="https://')
        start = body.find('"', href + 1)
        end = body.find('"', start + 1)
        url = body[start + 1:end]
        slash = url.find('/', 8)
        return url[slash:]

class RegisterHandlerTest(HandlerTestBase):
    # Tests normal account creation and confirmation.
    def testCreateAndConfirm(self):
        response = self.sendEmailPasswordPostRequest('/register', TEST_EMAIL, TEST_PASSWORD)
        #BUG: self.assertNoError(response) - success msg in response
        users = self.queryUsersByEmail(TEST_EMAIL)
        self.assertEqual(len(users), 1)
        self.assertFalse(users[0].verified)
        elapsed = (datetime.datetime.now() - users[0].join_date).total_seconds()
        self.assertLess(elapsed, 10)
        self.assertEqual(len(self.getSentEmails()), 1)
        self.assertEqual(self.getSentEmails()[0].to[0], TEST_EMAIL)
        path = self.getPathFromEmail(self.getSentEmails()[0])
        response = self.sendGetRequest(path, status=302)
        users = self.queryUsersByEmail(TEST_EMAIL)
        self.assertEqual(len(users), 1)
        self.assertTrue(users[0].verified)

    # Tests creating two account entries and verifying the second.
    def testCreateTwiceAndConfirm(self):
        response = self.sendEmailPasswordPostRequest('/register', TEST_EMAIL, TEST_PASSWORD)
        #BUG: self.assertNoError(response) - success msg in response
        users = self.queryUsersByEmail(TEST_EMAIL)
        self.assertEqual(len(users), 1)
        self.assertFalse(users[0].verified)
        self.assertEqual(len(self.getSentEmails()), 1)
        path = self.getPathFromEmail(self.getSentEmails()[0])
        response = self.sendEmailPasswordPostRequest('/register', TEST_EMAIL, TEST_PASSWORD)
        #BUG: self.assertNoError(response) - success msg in response
        users = self.queryUsersByEmail(TEST_EMAIL)
        self.assertEqual(len(users), 2)
        self.assertFalse(users[0].verified)
        self.assertFalse(users[1].verified)
        self.assertEqual(len(self.getSentEmails()), 2)
        path = self.getPathFromEmail(self.getSentEmails()[1])
        response = self.sendGetRequest(path, status=302)
        users = self.queryUsersByEmail(TEST_EMAIL)
        self.assertEqual(len(users), 1)
        self.assertTrue(users[0].verified)

    # Tests creating an account and trying to confirm it twice.
    # The second confirm should fail.
    def testCreateAndConfirmTwice(self):
        response = self.sendEmailPasswordPostRequest('/register', TEST_EMAIL, TEST_PASSWORD)
        #BUG: self.assertNoError(response) - success msg in response
        users = self.queryUsersByEmail(TEST_EMAIL)
        self.assertEqual(len(users), 1)
        self.assertFalse(users[0].verified)
        self.assertEqual(len(self.getSentEmails()), 1)
        path = self.getPathFromEmail(self.getSentEmails()[0])
        response = self.sendGetRequest(path, status=302)
        users = self.queryUsersByEmail(TEST_EMAIL)
        self.assertEqual(len(users), 1)
        self.assertTrue(users[0].verified)
        response = self.sendGetRequest(path, status=400)
        users = self.queryUsersByEmail(TEST_EMAIL)
        self.assertEqual(len(users), 1)
        self.assertTrue(users[0].verified)

    # Tests creating an account, resending the confirm email, and then
    # successfully confirming with the second email.
    def testCreateAndResend(self):
        response = self.sendEmailPasswordPostRequest('/register', TEST_EMAIL, TEST_PASSWORD)
        #BUG: self.assertNoError(response) - success msg in response
        self.assertEqual(len(self.getSentEmails()), 1)
        self.assertEqual(self.getSentEmails()[0].to[0], TEST_EMAIL)
        response = self.sendEmailPasswordPostRequest('/resend', TEST_EMAIL, TEST_PASSWORD)
        #BUG: self.assertNoError(response) - success msg in response
        self.assertEqual(len(self.getSentEmails()), 2)
        self.assertEqual(self.getSentEmails()[1].to[0], TEST_EMAIL)
        path = self.getPathFromEmail(self.getSentEmails()[1])
        response = self.sendGetRequest(path, status=302)
        users = self.queryUsersByEmail(TEST_EMAIL)
        self.assertEqual(len(users), 1)
        self.assertTrue(users[0].verified)

    def testCreateWithNonEpsEmail(self):
        response = self.sendEmailPasswordPostRequest('/register', NON_EPS_EMAIL, TEST_PASSWORD)
        self.assertHasError(response)

    def testCreateWithNonexistentEpsEmail(self):
        response = self.sendEmailPasswordPostRequest('/register', UNKNOWN_EPS_EMAIL, TEST_PASSWORD)
        self.assertHasError(response)

    def testCreateWithInvalidEpsEmail(self):
        response = self.sendEmailPasswordPostRequest('/register', INVALID_EPS_EMAIL, TEST_PASSWORD)
        self.assertHasError(response)

class LoginHandlerTest(HandlerTestBase):
    def testLogin(self):
        self.addVerifiedUser()
        self.assertFalse('SID' in self.test_app.cookies)
        response = self.sendEmailPasswordPostRequest('/login', TEST_EMAIL, TEST_PASSWORD)
        self.assertNoError(response)
        self.assertNotEqual(response.headers['Set-Cookie'], None)
        self.assertTrue('SID' in self.test_app.cookies)

    def testLoginWithNoAccount(self):
        response = self.sendEmailPasswordPostRequest('/login', TEST_EMAIL, TEST_PASSWORD)
        self.assertHasError(response)

    def testLoginWithUnconfirmedAccount(self):
        self.addUnverifiedUser()
        response = self.sendEmailPasswordPostRequest('/login', TEST_EMAIL, TEST_PASSWORD)
        self.assertHasError(response)

    def testLoginWithConfirmedAndUnconfirmedAccount(self):
        self.addVerifiedUser()
        self.addUnverifiedUser()
        response = self.sendEmailPasswordPostRequest('/login', TEST_EMAIL, TEST_PASSWORD)
        self.assertNoError(response)

    def testLoginWithBadPassword(self):
        self.addVerifiedUser()
        response = self.sendEmailPasswordPostRequest('/login', TEST_EMAIL, BAD_PASSWORD)
        self.assertHasError(response)

class LogoutHandlerTest(HandlerTestBase):
    def testLogout(self):
        self.addVerifiedUser()
        self.assertFalse('SID' in self.test_app.cookies)
        self.login()
        self.assertTrue('SID' in self.test_app.cookies)
        self.sendPostRequest('/logout')
        self.assertFalse('SID' in self.test_app.cookies)

class AdminHandlerTest(HandlerTestBase):
    def testLoadAdminPage(self):
        self.addAdminUser()
        self.loginAsAdmin()
        response = self.sendGetRequest('/admin')
        self.assertEqual(response.status_int, 200)

    def testResendVerificationEmails(self):
        now = datetime.datetime.now()
        self.addAdminUser()
        self.addUser("bbison@eastsideprep.org", "bison4ever", now, False)
        self.addUser("ggrasshopper@eastsideprep.org", "hophophop", now, False)
        self.addUser("doesnotexist@eastsideprep.org", "doesnotexist", now, False)

        self.loginAsAdmin()
        response = self.sendPostRequest('/admin/emailblast')
        self.assertEqual(response.status_int, 200)

        emails = self.getSentEmails()
        emails.sort(key=lambda mail: mail.to[0])
        self.assertEqual(self.getSentEmails()[0].to[0], "bbison@eastsideprep.org")
        self.assertEqual(self.getSentEmails()[1].to[0], "ggrasshopper@eastsideprep.org")
        self.assertEqual(len(self.getSentEmails()), 2)

class PrivacyHandlerTest(HandlerTestBase):
    def testReadAndSetPrivacy(self):
        self.addVerifiedUser()
        self.login()
        users = self.queryUsersByEmail(TEST_EMAIL)
        self.assertEqual(users[0].seen_update_dialog, False)
        self.assertEqual(users[0].share_photo, False)
        self.assertEqual(users[0].share_schedule, False)
        # get initial state
        response = self.sendGetRequest('/privacy')
        obj = json.loads(response.body)
        self.assertEqual(obj['share_photo'], False)
        self.assertEqual(obj['share_schedule'], False)
        users = self.queryUsersByEmail(TEST_EMAIL)
        self.assertEqual(users[0].seen_update_dialog, False)
        self.assertEqual(users[0].share_photo, False)
        self.assertEqual(users[0].share_schedule, False)
        # set share_photo to True
        response = self.sendPostRequest('/privacy', \
            'share_schedule=false&share_photo=true')
        self.assertEqual(response.status_int, 200)
        users = self.queryUsersByEmail(TEST_EMAIL)
        self.assertEqual(users[0].seen_update_dialog, True)
        self.assertEqual(users[0].share_photo, True)
        self.assertEqual(users[0].share_schedule, False)
        # refresh state
        response = self.sendGetRequest('/privacy')
        self.assertEqual(response.status_int, 200)
        obj = json.loads(response.body)
        self.assertEqual(obj['share_photo'], True)
        self.assertEqual(obj['share_schedule'], False)
        # set both to True
        response = self.sendPostRequest('/privacy', \
            'share_schedule=true&share_photo=true')
        self.assertEqual(response.status_int, 200)
        users = self.queryUsersByEmail(TEST_EMAIL)
        self.assertEqual(users[0].seen_update_dialog, True)
        self.assertEqual(users[0].share_photo, True)
        self.assertEqual(users[0].share_schedule, True)
        # one final check
        response = self.sendGetRequest('/privacy')
        self.assertEqual(response.status_int, 200)
        obj = json.loads(response.body)
        self.assertEqual(obj['share_photo'], True)
        self.assertEqual(obj['share_schedule'], True)

class ClassHandlerTest(HandlerTestBase):
    def testLoadClassData(self):
        self.addVerifiedUser()
        self.login()
        response = self.sendGetRequest('/class/greasy_burger_eating_7_8/a')
        response = self.sendGetRequest('/class/greasy_burger_eating_7_8/b', status=404)
        response = self.sendGetRequest('/class/does_not_exist/a', status=404)

class RoomHandlerTest(HandlerTestBase):
    def testLoadRoomData(self):
        self.addVerifiedUser()
        self.login()
        response = self.sendGetRequest('/room/hb_103')
        response = self.sendGetRequest('/room/hb_999', status=404)

class StudentHandlerTest(HandlerTestBase):
    def testLoadStudentData(self):
        self.addVerifiedUser()
        self.addUser('bbison@eastsideprep.org', 'bisons4ever', datetime.datetime.now(), True)
        self.login()
        response = self.sendGetRequest('/student/bulky_bison')
        response = self.sendGetRequest('/student/doesnot_exist', status=404)

class TeacherHandlerTest(HandlerTestBase):
    def testLoadTeacherData(self):
        self.addVerifiedUser()
        self.login()
        response = self.sendGetRequest('/teacher/steve_fassino')
        response = self.sendGetRequest('/teacher/doesnot_exist', status=404)

class SearchHandlerTest(HandlerTestBase):
    def testSearch(self):
        self.addVerifiedUser()
        self.login()
        response = self.sendGetRequest('/search/bulky')
        obj = json.loads(response.body)
        self.assertEqual(len(obj), 1)
        self.assertEqual(obj[0]['name'], 'Bulky Bison')
        self.assertEqual(obj[0]['prefix'], 'student')
        response = self.sendGetRequest('/search/steve')
        obj = json.loads(response.body)
        self.assertEqual(len(obj), 1)
        self.assertEqual(obj[0]['name'], 'Steve Fassino')
        self.assertEqual(obj[0]['prefix'], 'teacher')
        response = self.sendGetRequest('/search/a')
        obj = json.loads(response.body)
        self.assertEqual(len(obj), 3)
        response = self.sendGetRequest('/search/blarg')
        obj = json.loads(response.body)
        self.assertEqual(len(obj), 0)

class LunchesTest(HandlerTestBase):
    def testParseLunches(self):
        pass
        #update_lunch.test_read_lunches(TEST_LUNCH_PATH)
        #lunches = update_lunch.getLunchForDate(TEST_LUNCH_DATE)
        #for lunch in lunches: # Will only run once, but we need this
        #    self.assertEqual(lunch.summary, TEST_LUNCH_SUMMARY)
        #    self.assertEqual(lunch.description.length, LUNCH_DESCRIPTION_LENGTH)

# Untested handlers
#('/', MainHandler),
#('/about', AboutHandler),
#('/avatar/(\w+).jpg', AvatarHandler),
#('/logout', LogoutHandler),
#('/changepassword', ChangePasswordHandler),
#('/period/(\w+)', PeriodHandler),
#('/lunch', LunchRateHandler),
#('/cron/(\w+)', CronHandler),

if __name__ == '__main__':
    unittest.main()
