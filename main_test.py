import datetime
import json
import unittest
import webtest

import main  # module being tested
from main import User
from main import set_email_test
from main import get_sent_emails
# TODO(juberti): better way to hook sendgrid?

from google.appengine.api import datastore
from google.appengine.ext import db
from google.appengine.ext import testbed
from google.appengine.ext import vendor

vendor.add('lib')

from py_bcrypt import bcrypt

TEST_EMAIL = 'guberti@eastsideprep.org'
NON_EPS_EMAIL = 'test@example.org'
UNKNOWN_EPS_EMAIL = 'unknown@eastsideprep.org'
INVALID_EPS_EMAIL = 'invalid@eastsideprep.org'
TEST_PASSWORD = 'testtest'
BAD_PASSWORD = 'badbadbad'

class HandlerTestBase(unittest.TestCase):
    def setUp(self):
        # Test setup boilerplate.
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.test_app = webtest.TestApp(main.app)
        set_email_test(True) # hmmm

    def tearDown(self):
        set_email_test(False) # hmmm
        self.testbed.deactivate()

    def sendGetRequest(self, path, expect_errors = False):
        # PhantomJS uses WebKit, so Safari is closest to the truth.
        return self.test_app.get(path, headers = {'User-Agent': 'Safari'},
                                 expect_errors = expect_errors)

    def sendPostRequest(self, path, email, password):
        body = 'email={0}&password={1}'.format(email, password)
        return self.test_app.post(path, body, headers = {'User-Agent': 'Safari'})

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
        return get_sent_emails()

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
        response = self.sendPostRequest('/register', TEST_EMAIL, TEST_PASSWORD)
        self.assertEqual(response.status_int, 200)
        #BUG: self.assertNoError(response) - success msg in response
        users = self.queryUsersByEmail(TEST_EMAIL)
        self.assertEqual(len(users), 1)
        self.assertFalse(users[0].verified)
        elapsed = (datetime.datetime.now() - users[0].join_date).total_seconds()
        self.assertLess(elapsed, 10)
        self.assertEqual(len(self.getSentEmails()), 1)
        self.assertEqual(self.getSentEmails()[0].to[0], TEST_EMAIL)
        path = self.getPathFromEmail(self.getSentEmails()[0])
        response = self.sendGetRequest(path)
        self.assertEqual(response.status_int, 302)
        users = self.queryUsersByEmail(TEST_EMAIL)
        self.assertEqual(len(users), 1)
        self.assertTrue(users[0].verified)

    # Tests creating two account entries and verifying the second.
    def testCreateTwiceAndConfirm(self):
        response = self.sendPostRequest('/register', TEST_EMAIL, TEST_PASSWORD)
        self.assertEqual(response.status_int, 200)
        #BUG: self.assertNoError(response) - success msg in response
        users = self.queryUsersByEmail(TEST_EMAIL)
        self.assertEqual(len(users), 1)
        self.assertFalse(users[0].verified)
        self.assertEqual(len(self.getSentEmails()), 1)
        path = self.getPathFromEmail(self.getSentEmails()[0])
        response = self.sendPostRequest('/register', TEST_EMAIL, TEST_PASSWORD)
        self.assertEqual(response.status_int, 200)
        #BUG: self.assertNoError(response) - success msg in response
        users = self.queryUsersByEmail(TEST_EMAIL)
        self.assertEqual(len(users), 2)
        self.assertFalse(users[0].verified)
        self.assertFalse(users[1].verified)
        self.assertEqual(len(self.getSentEmails()), 2)
        path = self.getPathFromEmail(self.getSentEmails()[1])
        response = self.sendGetRequest(path)
        self.assertEqual(response.status_int, 302)
        users = self.queryUsersByEmail(TEST_EMAIL)
        self.assertEqual(len(users), 1) # TODO(juberti): figure out how this is possible
        self.assertTrue(users[0].verified)

    # Tests creating an account and trying to confirm it twice.
    # The second confirm should fail.
    def testCreateAndConfirmTwice(self):
        response = self.sendPostRequest('/register', TEST_EMAIL, TEST_PASSWORD)
        self.assertEqual(response.status_int, 200)
        #BUG: self.assertNoError(response) - success msg in response
        users = self.queryUsersByEmail(TEST_EMAIL)
        self.assertEqual(len(users), 1)
        self.assertFalse(users[0].verified)
        self.assertEqual(len(self.getSentEmails()), 1)
        path = self.getPathFromEmail(self.getSentEmails()[0])
        response = self.sendGetRequest(path)
        self.assertEqual(response.status_int, 302)
        users = self.queryUsersByEmail(TEST_EMAIL)
        self.assertEqual(len(users), 1)
        self.assertTrue(users[0].verified)
        response = self.sendGetRequest(path)
        self.assertEqual(response.status_int, 400)  # BUG: returning 200 but already confirmed...
        users = self.queryUsersByEmail(TEST_EMAIL)
        self.assertEqual(len(users), 1) # BUG: writing records on resend
        self.assertTrue(users[0].verified)

    # Tests creating an account, resending the confirm email, and then
    # successfully confirming with the second email.
    def testCreateAndResend(self):
        response = self.sendPostRequest('/register', TEST_EMAIL, TEST_PASSWORD)
        self.assertEqual(response.status_int, 200)
        #BUG: self.assertNoError(response) - success msg in response
        self.assertEqual(len(self.getSentEmails()), 1)
        self.assertEqual(self.getSentEmails()[0].to[0], TEST_EMAIL)
        response = self.sendPostRequest('/resend', TEST_EMAIL, TEST_PASSWORD)
        self.assertEqual(response.status_int, 200)
        #BUG: self.assertNoError(response) - success msg in response
        self.assertEqual(len(self.getSentEmails()), 2)
        self.assertEqual(self.getSentEmails()[1].to[0], TEST_EMAIL)
        path = self.getPathFromEmail(self.getSentEmails()[1])
        response = self.sendGetRequest(path)
        self.assertEqual(response.status_int, 302)
        users = self.queryUsersByEmail(TEST_EMAIL)
        self.assertEqual(len(users), 1)
        self.assertTrue(users[0].verified)

    def testCreateWithNonEpsEmail(self):
        response = self.sendPostRequest('/register', NON_EPS_EMAIL, TEST_PASSWORD)
        self.assertEqual(response.status_int, 200)
        self.assertHasError(response)

    def testCreateWithNonexistentEpsEmail(self):
        response = self.sendPostRequest('/register', UNKNOWN_EPS_EMAIL, TEST_PASSWORD)
        self.assertEqual(response.status_int, 200)
        self.assertHasError(response)

    def testCreateWithInvalidEpsEmail(self):
        response = self.sendPostRequest('/register', INVALID_EPS_EMAIL, TEST_PASSWORD)
        self.assertEqual(response.status_int, 200)
        self.assertHasError(response)

class LoginHandlerTest(HandlerTestBase):
    def testLogin(self):
        self.addVerifiedUser()
        response = self.sendPostRequest('/login', TEST_EMAIL, TEST_PASSWORD)
        self.assertEqual(response.status_int, 200)
        self.assertNoError(response)
        self.assertNotEqual(response.headers['Set-Cookie'], None)

    def testLoginWithNoAccount(self):
        response = self.sendPostRequest('/login', TEST_EMAIL, TEST_PASSWORD)
        self.assertEqual(response.status_int, 200)
        self.assertHasError(response)

    def testLoginWithUnconfirmedAccount(self):
        self.addUnverifiedUser()
        response = self.sendPostRequest('/login', TEST_EMAIL, TEST_PASSWORD)
        self.assertEqual(response.status_int, 200)
        self.assertHasError(response)

    def testLoginWithConfirmedAndUnconfirmedAccount(self):
        self.addVerifiedUser()
        self.addUnverifiedUser()
        response = self.sendPostRequest('/login', TEST_EMAIL, TEST_PASSWORD)
        self.assertEqual(response.status_int, 200)
        self.assertNoError(response)

    def testLoginWithBadPassword(self):
        self.addVerifiedUser()
        response = self.sendPostRequest('/login', TEST_EMAIL, BAD_PASSWORD)
        self.assertEqual(response.status_int, 200)
        self.assertHasError(response)

class AdminHandlerTest(HandlerTestBase):
    def testLoadAdminPage(self):
        pass

class ClassHandlerTest(HandlerTestBase):
    def testLoadClassData(self):
        pass

class RoomHandlerTest(HandlerTestBase):
    def testLoadRoomData(self):
        pass

class StudentHandlerTest(HandlerTestBase):
    def testLoadStudentData(self):
        pass

class TeacherHandlerTest(HandlerTestBase):
    def testLoadTeacherData(self):
        pass

if __name__ == '__main__':
    unittest.main()
