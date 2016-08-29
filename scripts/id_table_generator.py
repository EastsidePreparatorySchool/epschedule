# Code here generates a json table of usernames (e.g. guberti) and ids (e.g. 4093)

import string
import json

with open('../data/schedules.json') as data_file:    
    data = json.load(data_file)

EXCEPTIONS = {"estmary":"lstmary"}

def make_username(firstname, lastname):
    name = firstname[0] + lastname
    name = name.lower().replace(" ", "").replace(".", "")
    print name
    if name in EXCEPTIONS:
        return EXCEPTIONS[name]
    return name

output = []
for student in data:
    output.append([make_username(student["firstname"], student["lastname"]), student["id"]])

file = open('../data/id_table.json', 'wb')
file.write(json.dumps(output))