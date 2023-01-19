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
    id: int
    firstname: str
    preferred_name: str
    lastname: str
    lunch_id: int
    email: str
    gradyear: str
    photo_url: str

    def username(self):
        return self.email.split("@")[0]

    def display_name(self):
        return f"{self.preferred_name or self.firstname} {self.lastname}"

    def is_student(self):
        return not self.is_staff(self.id)

    def is_staff(self):
        return self.gradyear != "fac/staff"

    def class_of(self) -> Optional[int]:
        return int(self.gradyear) if self.is_student() else None


class Four11Client:
    def __init__(self):
        self._session = requests.Session()
        secret_client = secretmanager.SecretManagerServiceClient()
        secret_response = secret_client.access_secret_version(request=SECRET_REQUEST)
        self._api_key = secret_response.payload.data.decode("UTF-8")

    def _auth_header(self):
        return {"Authorization": "Bearer {}".format(self._api_key)}

    def api_key(self) -> str:
        return self._api_key

    def get_courses(self, username: str, term_id: int):
        response = self._session.get(
            COURSE_ENDPOINT_URL.format(username),
            headers=self._auth_header(),
            params={"term_id": str(term_id)},
        )
        response.raise_for_status()
        return json.loads(response.content)

    def get_people(self) -> List[Four11User]:
        response = self._session.get(PEOPLE_ENDPOINT_URL, headers=self._auth_header())
        response.raise_for_status()
        objs = json.loads(response.content)
        return [Four11User(**obj) for obj in objs]
