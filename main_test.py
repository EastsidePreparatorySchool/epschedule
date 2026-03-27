import json
import unittest

from app import app, init_app

with open("data/test_schedule.json", "r") as f:
    TEST_SCHEDULES = json.load(f)

TEST_MASTER_SCHEDULE = [
    {
        "2020-09-01": "Remote A-D_Rem",
        "2020-11-30": "End of Fall Term",
        "2021-03-30": "End of Winter Term",
    }
]


TEST_TEACHER = "jbriggs"
TEST_STUDENT = "bbison"
TEST_STUDENT_NO_PIC = "aaardvark"


class FakeKey:
    def __init__(self, kind, name):
        self.kind = kind
        self.name = name


class FakeEntity:
    def __init__(self, key):
        self.key = key
        self._data = {}

    def get(self, prop):
        if prop in self._data:
            return self._data[prop]
        return self.key.name != TEST_STUDENT_NO_PIC

    def items(self):
        # Privacy fields removed — return minimal user properties used in tests
        return self._data.items()

    def update(self, d):
        self._data.update(d)

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value


class FakeQuery:
    def __init__(self, store, kind):
        self._store = store
        self._kind = kind
        self._filters = []

    def add_filter(self, prop, op, value):
        self._filters.append((prop, op, value))

    def fetch(self):
        results = []
        for key, entity in self._store._entities.items():
            if key[0] != self._kind:
                continue
            match = True
            for prop, op, value in self._filters:
                if op == "=" and entity._data.get(prop) != value:
                    match = False
                    break
            if match:
                results.append(entity)
        return results


class FakeDatastore:
    def __init__(self):
        self._entities = {}

    def key(self, kind, name):
        return FakeKey(kind, name)

    def get(self, key):
        stored = self._entities.get((key.kind, key.name))
        if stored is not None:
            return stored
        return FakeEntity(key)

    def get_multi(self, keys):
        return [self.get(k) for k in keys]

    def put(self, entity):
        self._entities[(entity.key.kind, entity.key.name)] = entity

    def delete(self, key):
        self._entities.pop((key.kind, key.name), None)

    def query(self, kind=None):
        return FakeQuery(self, kind)


TEST_CONFIG = {
    "TESTING": True,
    "SECRET_KEY": bytes("test-key", "ascii"),
    "TOKEN": "test-token",
    "SCHEDULES": TEST_SCHEDULES,
    "MASTER_SCHEDULE": TEST_MASTER_SCHEDULE,
    "DATASTORE": FakeDatastore(),
}

API_ENDPOINTS = [
    "/student/aaardvark",
    "/class/a",
    "/period/a",
    "/search/aaardvark",
]


class NoAuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_app(TEST_CONFIG)

    def setUp(self):
        self.client = app.test_client()

    # Test that when not logged in, we're given a sign-in page.
    def test_main_login_response(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        # TODO kinda fragile
        self.assertIn("Sign in to EPSchedule", str(response.data))

    # Test that when not logged in, all API endpoints fail with a 403.
    def test_api_unauthorized(self):
        for endpoint in API_ENDPOINTS:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 403)

    # Test that username being set from cookies is what we want
    def test_login(self):
        self.client.set_cookie(
            key="token", value='{"email": "bbison@eastsideprep.org"}'
        )
        test_username = "bbison"
        with self.client as c:
            response = c.get("/")
            # Get username from session and compare it to actual one
            with c.session_transaction() as sess:
                self.assertEqual(sess["username"], test_username)

        self.assertEqual(response.status_code, 200)


AUTHENTICATED_USER = "bbison"


class AuthenticatedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_app(TEST_CONFIG)

    def setUp(self):
        self.client = app.test_client()
        with self.client.session_transaction() as sess:
            sess["username"] = AUTHENTICATED_USER

    def check_photo_url(self, url):
        self.assertTrue(
            url.startswith("https://epschedule-avatars.storage.googleapis.com/")
        )


class TestStudentEndpoint(AuthenticatedTest):
    """Tests for the /student endpoint."""

    def check_username(self, username):
        response = self.client.get(f"/student/{username}")
        self.assertEqual(response.status_code, 200)
        obj = json.loads(response.data)
        self.assertEqual(obj["username"], username)
        self.assertIn(obj["username"], obj["email"])
        self.assertEqual(len(obj["classes"]), 3)

        for trimester in obj["classes"]:
            # Could have 9 classes due to zero period
            self.assertGreaterEqual(len(trimester), 8)

        return obj

    # Test that the student method returns valid data for students and teachers.
    def test_get_student(self):
        teacher_obj = self.check_username(TEST_TEACHER)
        student_obj = self.check_username(TEST_STUDENT)

        # Teachers have no grade or gradyear
        self.assertIsNone(teacher_obj["grade"])
        self.assertIsNone(teacher_obj["gradyear"])

        # Students should, though
        self.assertGreaterEqual(student_obj["grade"], 5)
        self.assertGreaterEqual(student_obj["gradyear"], 2020)

    # Test that we can download the photo for a teacher.
    def test_has_photo(self):
        # Download teacher's profile photo to ensure it exists
        teacher_obj = self.check_username(TEST_TEACHER)
        self.check_photo_url(teacher_obj["photo_url"])

    # Test that a student who isn't sharing their pic returns a placeholder.
    def test_urls_showing_up(self):
        student_obj = self.check_username(TEST_STUDENT_NO_PIC)
        self.assertEqual(student_obj["photo_url"], "/static/images/placeholder.png")

    # Test that a student who is sharing their pic returns their pic
    def test_student_pics_showing_up(self):
        student_obj = self.check_username(TEST_STUDENT)
        self.assertNotEqual(student_obj["photo_url"], "/static/images/placeholder.png")


TEST_SEARCH = "b"


class TestSearchEndpoint(AuthenticatedTest):
    """Tests for the /search endpoint."""

    def test_search_endpoint(self):
        response = self.client.get("/search/{}".format(TEST_SEARCH))
        self.assertEqual(response.status_code, 200)
        results = json.loads(response.data)

        self.assertEqual(len(results), 2)
        for result in results:
            self.assertIn(TEST_SEARCH.lower(), result["name"].lower())


class TestClassEndpoint(AuthenticatedTest):
    """Tests for the /class endpoint."""

    # Test that we can get the fall A period class for the test user.
    def test_class_endpoint(self):
        response = self.client.get("/class/a?term_id=1")
        self.assertEqual(response.status_code, 200)
        _ = json.loads(response.data)

    # Test that any students who aren't sharing their pics return placeholders.
    def test_urls_inclass(self):
        response = self.client.get("/class/h?term_id=1")
        results = json.loads(response.data)
        students = results["students"]
        found_student = None
        for student in students:
            if student["username"] == TEST_STUDENT_NO_PIC:
                found_student = student
        self.assertNotEqual(found_student, None)
        # Simulate missing photo: should return placeholder
        self.assertEqual(
            found_student["photo_url"], "/static/images/placeholder_small.png"
        )


class TestPeriodEndpoint(AuthenticatedTest):
    """Tests for the /period endpoint."""

    def test_period_endpoint(self):
        response = self.client.get("/period/a")
        self.assertEqual(response.status_code, 200)
        results = json.loads(response.data)
        self.assertEqual(results["period"], "A")
        self.assertGreaterEqual(results["term_id"], 0)
        self.assertLessEqual(results["term_id"], 2)


class TestLogout(AuthenticatedTest):
    def test_logout(self):
        response = self.client.post("/logout")
        self.assertEqual(response.status_code, 200)
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Sign in to EPSchedule", str(response.data))


ADMIN_USER = "cwest"


class AdminTest(unittest.TestCase):
    """Base class for admin-authenticated tests."""

    @classmethod
    def setUpClass(cls):
        init_app(TEST_CONFIG)

    def setUp(self):
        self.client = app.test_client()
        with self.client.session_transaction() as sess:
            sess["username"] = ADMIN_USER


class TestPhotoRequestEndpointUnauth(unittest.TestCase):
    """Photo-request endpoints require authentication."""

    @classmethod
    def setUpClass(cls):
        init_app(TEST_CONFIG)

    def setUp(self):
        self.client = app.test_client()

    def test_photo_request_unauthenticated(self):
        response = self.client.post("/photo-request")
        self.assertEqual(response.status_code, 403)

    def test_admin_photo_requests_unauthenticated(self):
        response = self.client.get("/admin/photo-requests")
        self.assertEqual(response.status_code, 403)

    def test_approve_unauthenticated(self):
        response = self.client.post("/admin/photo-requests/bbison/approve")
        self.assertEqual(response.status_code, 403)

    def test_deny_unauthenticated(self):
        response = self.client.post("/admin/photo-requests/bbison/deny")
        self.assertEqual(response.status_code, 403)


class TestPhotoRequestEndpointNonAdmin(AuthenticatedTest):
    """Non-admin users cannot access admin photo-request endpoints."""

    def test_admin_list_forbidden(self):
        response = self.client.get("/admin/photo-requests")
        self.assertEqual(response.status_code, 403)

    def test_approve_forbidden(self):
        response = self.client.post("/admin/photo-requests/bbison/approve")
        self.assertEqual(response.status_code, 403)

    def test_deny_forbidden(self):
        response = self.client.post("/admin/photo-requests/bbison/deny")
        self.assertEqual(response.status_code, 403)


class TestPhotoRequestSubmit(AuthenticatedTest):
    """Tests for POST /photo-request (non-admin user uploading a photo)."""

    def _make_jpeg_bytes(self):
        """Return a minimal 10x10 JPEG as bytes."""
        import io

        from PIL import Image

        img = Image.new("RGB", (10, 10), color=(128, 64, 32))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()

    def test_no_file_returns_400(self):
        response = self.client.post("/photo-request", data={})
        self.assertEqual(response.status_code, 400)
        result = json.loads(response.data)
        self.assertIn("error", result)

    def test_invalid_file_returns_400(self):
        data = {"photo": (b"not-an-image", "bad.jpg")}
        response = self.client.post(
            "/photo-request",
            data=data,
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)

    def test_valid_jpeg_accepted(self):
        import io

        jpeg_bytes = self._make_jpeg_bytes()
        data = {"photo": (io.BytesIO(jpeg_bytes), "photo.jpg")}
        response = self.client.post(
            "/photo-request",
            data=data,
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertTrue(result.get("success"))


class TestAdminPhotoRequests(AdminTest):
    """Tests for admin photo-request management endpoints."""

    def _seed_request(self, username):
        """Directly insert a fake pending request into FakeDatastore."""
        import app as app_module

        ds = app_module.datastore_client
        key = ds.key("photo_request", username)
        entity = ds.get(key)
        entity.update(
            {
                "username": username,
                "submitted": __import__("datetime").datetime(2024, 1, 1),
                "status": "pending",
            }
        )
        ds.put(entity)

    def test_list_returns_pending(self):
        self._seed_request("bbison")
        response = self.client.get("/admin/photo-requests")
        self.assertEqual(response.status_code, 200)
        results = json.loads(response.data)
        usernames = [r["username"] for r in results]
        self.assertIn("bbison", usernames)

    def test_deny_request(self):
        self._seed_request("bbison")
        response = self.client.post("/admin/photo-requests/bbison/deny")
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertTrue(result.get("success"))

    def test_approve_request_no_storage(self):
        """Approve without a real storage client: photo fetch will fail gracefully."""
        self._seed_request("bbison")
        response = self.client.post("/admin/photo-requests/bbison/approve")
        # storage_client is None in tests, so the blob download is skipped and
        # the entity is marked approved – expect a 200 success response.
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertTrue(result.get("success"))


if __name__ == "__main__":
    unittest.main()
