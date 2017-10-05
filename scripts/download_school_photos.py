import json
import urllib

with open('../data/schedules.json') as data_file:    
    data = json.load(data_file)

for student in data:
	photo_url = "http://four11.eastsideprep.org/system/"
	if (student["grade"] != None):
		photo_url += "students"
	else:
		photo_url += "teachers"
	photo_url += "/idphotos/000/00"

	sid = str(student['sid'])

	if (len(sid) == 3):
		photo_url += "0/" + sid
	else: # If length is 4
		photo_url += sid[0] + "/" + sid[1:]

	photo_url += "/medium/"
	photo_url += student["lastname"].replace(" ", "_").replace(".", "") + "__" + student["firstname"] + ".jpg"
	print photo_url

	urllib.urlretrieve(photo_url, "../school_photos/" + student["lastname"].lower().replace(" ", "").replace(".", "") + "_" + student["firstname"].lower() + ".jpg")