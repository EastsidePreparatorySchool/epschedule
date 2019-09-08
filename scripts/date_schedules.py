from datetime import date, timedelta
import urllib
import json

BASE_URL = "https://four11.eastsideprep.org/epsnet/schedule_for_date?date="

START_DATE = date(2019, 9, 4)
END_DATE = date(2020, 6, 29)

delta = END_DATE - START_DATE
schedules = {}
days = {}


def make_url(d):
	return BASE_URL + str(d)

def download_json(d):
	url = make_url(d)
	response = urllib.urlopen(url)
	return json.loads(response.read())

for i in range (delta.days + 1):
	d = START_DATE + timedelta(days=i)
	print "Fetching " + str(d)

	if d.weekday() >= 5: # If day is a weekend
		# We don't write weekends to database, so skip it
		continue

	data = download_json(d)

	# On days without school
	if not 'schedule_day' in data:
		days[str(d)] = None
		continue

	name = data['schedule_day']
	# Yes, we need both these lines
	if 'activity_day' in data:
		if data['activity_day']:
			name += "_" + data['activity_day'][:3]

	if not name in schedules:
		schedules[name] = data['periods']

	days[str(d)] = name

exception_table = [days, schedules]

file = open('../data/exceptions.json', 'w')
file.write(json.dumps(exception_table))

file = open('../data/exceptions_pretty.json', 'w')
file.write(json.dumps(exception_table, indent=4))
