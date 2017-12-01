import string
import json

with open('../data/schedules_pretty.json') as data_file:    
    data = json.load(data_file)

for person in data:
	error = False

	# Teacher error repairs
	if not person['gradyear']: # If they're a student
		continue
			
	for clss in person['classes']:

		if clss['name'] == "Modern Perspectives: Late 19th and Early 20th Century European Literature" and clss['period'] == "C" and clss['room'] == 'AX-104':
			clss['teacher'] = 'Ryan Aponte'
			print "Fixed!"
			print person['firstname'] + " " + person['lastname']
		'''if clss['name'] != "Free Period" and not clss['room']:
			error = True
			repaired = False

			# Student error repairs
			# Try to repair the error
			for otherperson in data:
				for otherclass in otherperson['classes']:
					if clss['name'] == otherclass['name'] and clss['period'] == otherclass['period'] and clss['teacher'] == otherclass['teacher'] and otherclass['room']:
						clss['room'] = otherclass['room']
						repaired = True
						break

				if repaired:
					print "Error repaired"
					break


			for otherperson in data:
				for otherclass in otherperson['classes']:
					if clss['name'] == otherclass['name'] and clss['period'] == otherclass['period'] and otherclass['teacher'] == (person['firstname'] + " " + person['lastname']) and otherclass['room']:
						clss['room'] = otherclass['room']
						repaired = True
						break

				if repaired:
					print "Error repaired"
					break'''



# Repair the errors

#file = open('../data/schedules.json', 'w')
#file.write(json.dumps(data))

#file = open('../data/schedules_pretty.json', 'w')
#file.write(json.dumps(data, indent=4))