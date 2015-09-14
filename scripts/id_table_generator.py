from os import listdir
import string
import json
files = listdir("C:/Users/guberti/Documents/Github/EPSchedule/schedules")
output = []
for filename in files:
    filename = filename[:-4]
    filename = filename.lower()
    filename = filename.replace(" ", "")
    filenamelist = string.split(filename, "-")
    studentid = int(filenamelist[0])
    firstinitial = filenamelist[3][0]
    lastname = filenamelist[2]
    studentname = firstinitial + lastname
    output.append([studentname, studentid])
print output
file = open('..\\id_table.json', 'wb')
file.write(json.dumps(output))