from types import SimpleNamespace

from cron import schedules


def make_response(username="ajosan", birthday=None):
    individual = {
        "id": 1,
        "firstname": "Anmol",
        "lastname": "Josan",
        "gradyear": 2027,
        "email": f"{username}@eastsideprep.org",
        "office": None,
        "birthday": birthday,
        "early_dismissal": False,
    }
    return {
        "individual": individual,
        "sections": [],
    }


class FakeClient:
    def __init__(self, people, birthday=None):
        self.people = people
        self.birthday = birthday

    def get_people(self):
        return self.people

    def get_courses(self, username, term_id):
        response = make_response(username, self.birthday)
        response["sections"] = [
            {
                "period": "A",
                "location": "Room 1",
                "course": "Test Course",
                "teacher": "teacher",
                "department": "Test",
            }
        ]
        return response


def fake_person(username):
    return SimpleNamespace(username=lambda: username)


def test_download_schedule_omits_four11_missing_birthday():
    client = FakeClient([fake_person("ajosan")], birthday="03/14")

    result = schedules.download_schedule(client, "ajosan", 2027)

    assert "birthday" not in result


def test_download_schedule_keeps_real_birthday():
    client = FakeClient([fake_person("ajosan")], birthday="11/02")

    result = schedules.download_schedule(client, "ajosan", 2027)

    assert result["birthday"] == "11/02"


def test_crawl_schedules_filters_to_target_username(monkeypatch):
    people = [fake_person("ajosan"), fake_person("other")]
    client = FakeClient(people, birthday="11/02")
    uploaded = {}

    class FakeBlob:
        def download_as_string(self):
            return b'{"other": {"username": "other"}}'

        def upload_from_string(self, value):
            uploaded["value"] = value

    class FakeBucket:
        def blob(self, name):
            assert name == "schedules.json"
            return FakeBlob()

    monkeypatch.setattr(schedules.four11, "Four11Client", lambda: client)
    monkeypatch.setattr(
        schedules.storage,
        "Client",
        lambda: SimpleNamespace(bucket=lambda _: FakeBucket()),
    )

    schedules.crawl_schedules(target_username="ajosan")

    assert '"ajosan"' in uploaded["value"]
    assert '"other"' in uploaded["value"]
