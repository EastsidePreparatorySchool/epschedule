# Code here generates a json table of usernames (e.g. guberti) and ids (e.g. 4093)

from os import listdir
import string
import json
files = listdir("C:/Users/guberti/Documents/Github/EPSchedule/schedules")
output = []
for filename in files:
    filename = filename[:-4]  # Remove .pdf extension
    filename = filename.lower()
    filename = filename.replace(" ", "")  # Remove spaces
    filenamelist = string.split(filename, "-")  # 9999-1-Lastname-Firstname becomes ["9999", "1", "Lastname", "Firstname"]
    studentid = int(filenamelist[0])
    firstinitial = filenamelist[3][0]
    lastname = filenamelist[2]
    studentusername = firstinitial + lastname
    output.append([studentusername, studentid])

file = open('..\\id_table.json', 'wb')
file.write(json.dumps(output))