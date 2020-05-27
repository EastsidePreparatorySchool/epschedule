import datetime
import hashlib
import json
import time


import requests
from google.cloud import secretmanager, storage


ENDPOINT_URL = "https://four11.eastsideprep.org/epsnet/courses/"
PARSEABLE_PERIODS = ["A", "B", "C", "D", "E", "F", "G", "H"]
FREE_PERIOD_CLASS = {
    "room": None,
    "name": "Free Period",
    "teacher": None,
    "teacher_username": None,
    "department": None,
}

def get_full_name(username):
    for p in id_table:
        if p["username"].lower() == username.lower():
            return p["firstname"] + " " + p["lastname"]
    return None

# Return the year of the current graduating class
# I.E. the 2019-2020 school year would return 2020
def get_current_school_year():
    now = datetime.datetime.now()
    end_year = now.year
    if now.month >= 7 or (now.month >= 6 and now.day >= 10):
        # Old school year has ended, add one to year
        end_year += 1
    return end_year

def add_free_periods_to_schedule(course_list):
    for period in PARSEABLE_PERIODS:
        contains = False
        for clss in course_list:
            if clss["period"] == period:
                contains = True
                break

        if not contains:
            course_list.append(FREE_PERIOD_CLASS.copy())
            course_list[-1]["period"] = period
    # Modifies course list in place

def decode_trimester_classes(four11_response):
    trimester_classes = []
    trimester = four11_response["sections"]
    for clss in trimester:
        if clss["period"] in PARSEABLE_PERIODS:
            obj = {
                "period": clss["period"],
                "room": clss["location"],
                "name": clss["course"],
                "teacher": get_full_name(clss["teacher"]),
                "teacher_username": clss["teacher"],
                "department": clss["department"],
            }
            trimester_classes.append(obj)

    add_free_periods_to_schedule(trimester_classes)
    trimester_classes.sort(key=lambda x: x["period"])
    return trimester_classes

def get_json_schedule_data(id_table):
    schedules = []
    school_year = get_current_school_year()

    for item in id_table:
        #if item['username'] == 'amurray':
        #    continue
        try:
            person = {"classes": []}

            # For each trimester
            for term_id in range(1, 4):
                req = requests.post(
                    ENDPOINT_URL + item["username"], headers=AUTH_HEADERS, params={"term_id": str(term_id)}
                )
                #print req.content
                briggs_person = json.loads(req.content)
                person["classes"].append(decode_trimester_classes(briggs_person))

            person.update(item)
            person["sid"] = person.pop("id") # Rename key
            person["nickname"] = briggs_person["individual"]["nickname"]

            # Find advisor
            person["advisor"] = None
            for section in briggs_person["sections"]:
                if "advisory" in section["course"].lower():
                    person["advisor"] = get_full_name(section["teacher"])

            # Convert grade to gradyear
            person["grade"] = None
            if person["gradyear"]:
                person["grade"] = 12 - (person["gradyear"] - school_year)

            # Now we have finished the person object
            schedules.append(person)
            print ("Decoded " + person["username"])
            time.sleep(1)

        except ValueError:
            print("Got value error for " + str(item))

    return json.dumps(schedules, indent=4)

# Read the data table from which we'll build our schedules
with open('../data/id_table.json') as data_file:
    id_table = json.load(data_file)

file = open('../data/schedules.json', 'w')
file.write(get_json_schedule_data(id_table))


def crawl_schedules(event):
    print("Crawling")
    start = time.time()
    # Load access key
    secret_client = secretmanager.SecretManagerServiceClient()
    key = secret_client.access_secret_version(
        "projects/epschedule-v2/secrets/four11_key/versions/1"
    ).payload.data
    print(key)
    return


    # Open the bucket
    storage_client = storage.Client()
    data_bucket = storage_client.bucket("epschedule-data")

    schedule_blob = data_bucket.blob("schedules.json")
    schedules = json.loads(schedule_blob.download_as_string())

    rawdir = tempfile.mkdtemp()
    croppeddir = tempfile.mkdtemp()

    for schedule in schedules:
        photo = download_photo(schedule)
        if photo is None:
            continue
        fullsize_filename = hash_username(key, schedule["username"])
        upload_photo(avatar_bucket, fullsize_filename, photo)

        # Now crop photo
        cropped = crop_image(photo)
        icon_filename = hash_username(key, schedule["username"], icon=True)
        upload_photo(avatar_bucket, icon_filename, cropped)

        # For teachers, upload an unhashed grayscale photo
        if not schedule["grade"]:
            grayscale = cropped.convert("L")
            upload_photo(avatar_bucket, schedule["username"] + ".jpg", grayscale)

    print("Operation took {:.2f} seconds".format(time.time() - start))


if __name__ == "__main__":
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "../epschedule-455d8a10f5ec.json"
    print("Foo")
    crawl_schedules(event)
