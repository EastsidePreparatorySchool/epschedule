import json
import string

with open('../data/schedules.json') as data_file:
    schedules = json.load(data_file)

with open('../data/bios.json') as data_file:
    bios = json.load(data_file)

for teacher in schedules:
    if not teacher['grade']: # If they are a teacher
        found = False
        abb = (teacher['firstname'] + "_" + teacher['lastname']).lower()

        for person in bios:
            if person['name'] == abb:
                found = True
                break

        if not found:
            bios.append({"bio": "", "name": abb})

file = open('../data/bios.json', 'w')
file.write(json.dumps(bios))
