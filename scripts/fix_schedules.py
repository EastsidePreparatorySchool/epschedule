import json

with open('../data/schedules.json') as data_file:
    students = json.load(data_file)

for student in students:
    if not student['gradyear']: # If they're a teacher
        continue # Skip over teachers

    for clss in student['classes']:
        if clss['name'] != "Free Period" and not clss['room']:

            # We need to try to find the room
            for teststudent in students:
                if not teststudent['gradyear']: # If they're a teacher
                    continue # Skip over teachers

                for testclass in teststudent['classes']:
                    if testclass['name'] == clss['name'] and testclass['teacher'] == clss['teacher'] and testclass['period'] == clss['period'] and testclass['room']:
                        clss['room'] = testclass['room']
                        print "Fixed " + student['username'] + "'s class " + clss['name']

file = open('../data/schedules.json', 'w')
file.write(json.dumps(students))