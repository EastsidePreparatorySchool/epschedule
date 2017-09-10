import csv
import string
import json

def conv_gradyear(stryear):
	if stryear == "NULL":
		return None
	else:
		return int(stryear)

jsonarr = []
isheader = True
students = 0

with open('../data/user_ids_four11.csv', 'rb') as f:
    reader = csv.reader(f)
    for row in reader:
    	if isheader:
    		isheader = False
    		continue

        obj = {'id': int(row[0]), 'firstname': row[1], 'lastname': row[3], \
        'username': string.split(row[5], "@")[0].lower(), 'gradyear': conv_gradyear(row[6])}

        if obj['gradyear']:
        	students += 1

        jsonarr.append(obj)


jsonarr.sort(key=lambda x: x["id"])

data = json.dumps(jsonarr)

print "Writing data to disk..."

file = open('../data/id_table.json', 'wb')
file.write(data)

print data

print "Wrote " + str(len(jsonarr)) + " usernames to disk. " + str(students) + " were students and " + str(len(jsonarr) - students) + " were teachers."