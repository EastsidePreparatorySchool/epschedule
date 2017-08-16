import os
import json
import string

with open('../data/schedules.json') as data_file:
    id_table = json.load(data_file)

files = [f for f in os.listdir('..' + os.sep + 'teacher_photos')] #Create a list of all files in the directory

for teacher in id_table:
    if not teacher['gradyear']: # If they are a teacher

        # Test if they teach any classes
        teaches = False
        n = ""

        for clss in teacher['classes']:
            if clss['name'] != "Free Period":
                print n
                n = clss['name']
                teaches = True
                break

        if not teaches:
            continue

        filename = (teacher['firstname'] + "_" + teacher['lastname']).lower()
        
        # Now see if we have that photo
        found = False

        for f in files:
            names = string.split(f, ".")[0]

            if filename == names:
                found = True
                break

        if not found:
            print teacher['firstname'] + "_" + teacher['lastname'] + " teaches " + n
            print "Missing photo for " + teacher['firstname'] + " " + teacher['lastname']
            print ""