# Code here generates a json table of usernames (e.g. guberti) and ids (e.g. 4093)

from os import listdir
import string
import json

EXCEPTIONS = {"estmary":"lstmary"}

def make_username(firstname, lastname):
    name = firstname[0] + lastname
    print name
    if name in EXCEPTIONS:
        return EXCEPTIONS[name]
    return name

files = listdir("C:/Users/guberti/Documents/Github/EPSchedule/schedules")
output = []
for filename in files:
    filename = filename[:-4]  # Remove .pdf extension
    filename = filename.lower()
    filename = filename.replace(".", "")
    filename = filename.replace(" ", "")  # Remove spaces
    filenamelist = string.split(filename, "-")  # 9999-1-Lastname-Firstname becomes ["9999", "1", "Lastname", "Firstname"]
    studentid = int(filenamelist[0])
    firstname = filenamelist[3]
    lastname = filenamelist[2]
    output.append([make_username(firstname, lastname), studentid])

file = open('../data/id_table.json', 'wb')
file.write(json.dumps(output))