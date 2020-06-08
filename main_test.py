from io import BytesIO
import json
import unittest
import requests

from PIL import Image

from main import app

''' Note - these tests run entirely on PRODUCTION data, so
service account credentials are needed for them to pass.
This stems from my belief that tests not using fake data
are less scientifically valid (i.e. drug testing on humans
is more valid than testing on mice) and from a desire to
not have production and test versions of each dataset'''

API_ENDPOINTS = [
    "/student/guberti",
    "/class/a",
    "/period/a",
    "/search/guberti"
]


def download_photo(url):
    r = requests.get(url, stream=True)
    return Image.open(BytesIO(r.content))

class NoAuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_main_login_response(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        # TODO kinda fragile
        self.assertIn("Sign in to EPSchedule", str(response.data))

    def test_api_unauthorized(self):
        for endpoint in API_ENDPOINTS:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 403)

# TODO fix this not to break when auberti graduates
AUTHENTICATED_USER = "auberti"

class AuthenticatedTest(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        with self.client.session_transaction() as sess:
            sess["username"] = AUTHENTICATED_USER

TEST_TEACHER = "jbriggs"
TEST_STUDENT = "auberti"

class TestStudentEndpoint(AuthenticatedTest):
    def check_username(self, username):
        response = self.client.get('/student/{}'.format(username))
        self.assertEqual(response.status_code, 200)

        obj = json.loads(response.data)
        self.assertEqual(obj["username"], username)
        self.assertIn(obj["username"], obj["email"])
        self.assertEqual(len(obj["classes"]), 3)

        for trimester in obj["classes"]:
            # Could have 9 classes due to zero period
            self.assertGreaterEqual(len(trimester), 8)

        return obj

    def test_get_student(self):
        teacher_obj = self.check_username(TEST_TEACHER)
        student_obj = self.check_username(TEST_STUDENT)

        # Teachers have no grade or gradyear
        self.assertIsNone(teacher_obj["grade"])
        self.assertIsNone(teacher_obj["gradyear"])

        # Students should, though
        self.assertGreaterEqual(student_obj["grade"], 5)
        self.assertGreaterEqual(student_obj["gradyear"], 2020)

    def test_has_photo(self):
        # Download teacher's profile photo to ensure it exists
        teacher_obj = self.check_username(TEST_TEACHER)
        photo = download_photo(teacher_obj["photo_url"])

        # Make sure the photo isn't an icon
        self.assertGreater(photo.width, 96)
        self.assertGreater(photo.height, 96)


if __name__ == "__main__":
    unittest.main()
