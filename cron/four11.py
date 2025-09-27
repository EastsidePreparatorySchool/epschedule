import dataclasses
import json
from typing import List, Optional

import requests
from google.cloud import secretmanager

PEOPLE_ENDPOINT_URL = "https://four11.eastsideprep.org/epschedule/people"
COURSE_ENDPOINT_URL = "https://four11.eastsideprep.org/epsnet/courses/{}"
SECRET_REQUEST = {"name": "projects/epschedule-v2/secrets/four11_key/versions/1"}


@dataclasses.dataclass
class Four11User:
    # stores a student from four11
    # uses its ID (Lunch ID), first and last name, email, grad year, url, and pref name
    id: int
    firstname: str
    lastname: str
    lunch_id: int
    email: str
    gradyear: str
    photo_url: str
    preferred_name: Optional[str] = None

    def username(self):
        # returns the front thing before email @
        return self.email.split("@")[0]

    def display_name(self):
        # python default uses pref name since it's listed first
        return f"{self.preferred_name or self.firstname} {self.lastname}"

    def is_student(self):
        # checks if its a student
        # its just if it isnt a staff
        return not self.is_staff()

    def is_staff(self):
        # check if its a staff
        return self.gradyear == "fac/staff"

    def class_of(self) -> Optional[int]:
        # returns graduation year of student
        return int(self.gradyear) if self.is_student() else None


class Four11Client:
    def __init__(self):
        # starts a session
        self._session = requests.Session()
        # requests secrets
        secret_client = secretmanager.SecretManagerServiceClient()
        secret_response = secret_client.access_secret_version(request=SECRET_REQUEST)
        # sets API key based on decoded secret
        self._api_key = secret_response.payload.data.decode("UTF-8")

    def _auth_header(self):
        # returns the authorization from the API key
        return {"Authorization": "Bearer {}".format(self._api_key)}

    def api_key(self) -> str:
        # returns the API key
        return self._api_key

    def get_courses(self, username: str, term_id: int):
        # get courses based on student
        response = self._session.get(
            COURSE_ENDPOINT_URL.format(username),
            headers=self._auth_header(),
            params={"term_id": str(term_id)},
        )
        response.raise_for_status()
        # load it into JSON
        return json.loads(response.content)

    def get_people(self) -> List[Four11User]:
        # returns a list of Four11User objects
        response = self._session.get(PEOPLE_ENDPOINT_URL, headers=self._auth_header())
        response.raise_for_status()
        # grabs the json loads things from the response
        objs = json.loads(response.content)
        # creates four11users from input objects
        return [Four11User(**obj) for obj in objs]
