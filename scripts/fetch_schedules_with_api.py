import requests
import json
import datetime
import time

ENDPOINT_URL = "https://four11.eastsideprep.org/epsnet/courses/"
PARSEABLE_PERIODS = ["A", "B", "C", "D", "E", "F", "G", "H"]
FOUR11_KEY_PATH ="../data/four11.key"
FREE_PERIOD_CLASS = {
    "room": None,
    "name": "Free Period",
    "teacher_full_name": None,
    "teacher_username": None,
    "department": None,
}

with open(FOUR11_KEY_PATH) as key:
    FOUR11_KEY = key.read()
AUTH_HEADERS = {"Authorization": "Bearer " + FOUR11_KEY}

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
                "teacher_full_name": get_full_name(clss["teacher"]),
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
            print "Trying to decode classes for " + str(item)

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
            time.sleep(5)

        except ValueError:
            print "Got value error for " + str(item)

    return json.dumps(schedules, indent=4)

# Read the data table from which we'll build our schedules
with open('../data/id_table.json') as data_file:
    id_table = json.load(data_file)

file = open('../data/schedules.json', 'w')
file.write(get_json_schedule_data(id_table))
