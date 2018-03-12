import requests
import json
import datetime

url = 'https://four11.eastsideprep.org/epsnet/courses/'
PARSEABLE_PERIODS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
# Properly set up headers with auth key
with open('../data/four11.key') as key:    
    four11_key = key.read()
headers = {"Authorization": "Bearer " + four11_key}

# Read the data table from which we'll build our schedules
with open('../data/id_table.json') as data_file:    
    data = json.load(data_file)

def get_full_name(username):
    for p in data:
        if p["username"].lower() == username.lower():
            return p["firstname"] + " " + p["lastname"]
    return None

def getinfo(x):
    print x
    return x['period']

schedules = []

# Find what the year will be at the 
# end of the school year
now = datetime.datetime.now()
end_year = now.year
if now.month >= 7 or (now.month >= 6 and now.day >= 10):
    # Old school year has ended, add one to year
    end_year += 1

for item in data:
    #if item['username'] == "tkrauss-mcclurg":
    #    continue
    req = requests.post(url + item['username'], headers=headers, params={"term_id": "3"})
    briggs_person = json.loads(req.content)

    # Parse all the person info
    person = {}
    person['firstname'] = item['firstname']
    person['lastname'] = item['lastname']
    person['username'] = item['username']
    person['sid'] = item['id']
    person['gradyear'] = item['gradyear']
    person['nickname'] = briggs_person['individual']['nickname']

    # Find advisor
    person['advisor'] = None
    for section in briggs_person['sections']:
        if 'advisory' in section['course'].lower():
            person['advisor'] = get_full_name(section['teacher'])

    # Convert grade to gradyear
    person['grade'] = None
    if person['gradyear']:
        person['grade'] = 12 - (person['gradyear'] - end_year)

    # We now have all personal information that we need
    # Now, we'll go trimester by trimester and parse schedules
    person['classes'] = []

    trimester = json.loads(req.content)['sections']

    for clss in trimester:
        if clss['period'] in PARSEABLE_PERIODS:
            obj = {
                'period': clss['period'], \
                'room': clss['location'], \
                'name': clss['course'], \
                'teacher': get_full_name(clss['teacher']), \
                'department': clss['department'] \
            }
            person['classes'].append(obj)

    # Now, check to see if we need to add free period(s)
    for period in PARSEABLE_PERIODS:
        contains = False
        for clss in person['classes']:
            if clss['period'] == period:
                contains = True
                break

        if not contains:
            person['classes'].append({
                "period": period, \
                "room": None, \
                "name": "Free Period", \
                "teacher": None, \
                "department": None
            })

    # Now sort A-H
    person['classes'].sort(key=lambda x: x['period'])

    # Now we have finished the person object
    schedules.append(person)
    print "Decoded " + person['username']

file = open('../data/schedules.json', 'w')
file.write(json.dumps(schedules, indent=4))