import json
import time
from datetime import date, timedelta
from urllib import request
from urllib.error import HTTPError

BASE_URL = "https://four11.eastsideprep.org/epsnet/schedule_for_date?date="

START_DATE = date(2022, 8, 30)
END_DATE = date(2023, 6, 10)

delta = END_DATE - START_DATE
schedules = {}
days = {}


def make_url(day):
    return BASE_URL + str(day)


def download_json_with_retry(d):
    for i in range(3):
        try:
            return download_json(d)
        except HTTPError as e:
            print("Error: " + e + ", retrying")
            if i != 2:
                time.sleep(1)
            else:
                raise e


def download_json(day):
    url = make_url(day)
    response = request.urlopen(url)
    return json.loads(response.read())


def download_exceptions():
    for i in range(delta.days + 1):
        day = START_DATE + timedelta(days=i)
        print("Fetching " + str(day))

        if day.weekday() >= 5:  # If day is a weekend
            # We don't write weekends to database, so skip it
            continue

        data = download_json_with_retry(day)

        # On days without school
        if not "schedule_day" in data:
            days[str(day)] = None
            continue

        name = data["schedule_day"]
        if name is None:
            continue

        # Yes, we need both these lines
        # take this out at some point!
        if "activity_day" in data:
            if data["activity_day"]:
                name += "_" + data["activity_day"][:3]

        if not name in schedules:
            schedules[name] = data["periods"]

        days[str(day)] = name

    exception_table = [days, schedules]

    with open("../data/master_schedule.json", "w") as file:
        file.write(json.dumps(exception_table, indent=4, sort_keys=True))


if __name__ == "__main__":
    download_exceptions()
