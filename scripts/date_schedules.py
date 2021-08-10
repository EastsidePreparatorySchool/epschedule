from datetime import date, timedelta
from urllib import request
import json

BASE_URL = "https://four11.eastsideprep.org/epsnet/schedule_for_date?date="

START_DATE = date(2021, 9, 8)
END_DATE = date(2021, 11, 21 )

delta = END_DATE - START_DATE
schedules = {}
days = {}


def make_url(d):
	return BASE_URL + str(d)

def download_json_with_retry(d):
	for i in range (3): 
		try:
			return download_json(d)
		except urllib.error.HTTPError as e:
			print(e)


def download_json(d):
	url = make_url(d)
	response = request.urlopen(url)
	return json.loads(response.read())

for i in range (delta.days + 1):
	d = START_DATE + timedelta(days=i)
	print("Fetching " + str(d))

	if d.weekday() >= 5: # If day is a weekend
		# We don't write weekends to database, so skip it
		continue

	data = download_json_with_retry(d)

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
print(exception_table)

file = open('../data/master_schedule.json', 'w')
file.write(json.dumps(exception_table, indent=4, sort_keys=True))
