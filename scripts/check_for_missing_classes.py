import string
import json

with open('../data/schedules_pretty.json') as data_file:    
    data = json.load(data_file)

for person in data:
	freenum = 0

	# Teacher error repairs
	if not person['gradyear']: # If they're a teacher
		continue
			
	for clss in person['classes']:
		if clss['name'] == "Free Period":
			freenum += 1

	if freenum > 3:
		print person['firstname'] + " " + person['lastname'] + " has " + str(freenum) + " free periods"

file = open('../data/schedules.json', 'w')
file.write(json.dumps(data))