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

	if (len(student["id"]) == 3):
		photo_url += "0/" + student["id"]
	else: # If length is 4
		photo_url += student["id"][0] + "/" + student["id"][1:]

	photo_url += "/medium/"
	photo_url += student["lastname"].replace(" ", "_").replace(".", "") + "_" + student["firstname"] + "_" + student["id"] + ".jpg"
	print photo_url

	urllib.urlretrieve(photo_url, "../school_photos/" + student["lastname"].lower().replace(" ", "").replace(".", "") + "_" + student["firstname"].lower() + ".jpg")