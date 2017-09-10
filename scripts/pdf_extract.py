from collections import OrderedDict
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from pdfminer.converter import PDFPageAggregator
from cStringIO import StringIO
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFTextExtractionNotAllowed
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfdevice import PDFDevice
from pdfminer.layout import LTTextBox
import string
import os, sys
import json
from datetime import date

DO_NOT_PARSE = ["4491-1-Mein-Angelika.pdf"]
UPPER_SCHOOL_STUDY_HALL_PERIODS = {"A": "OH-102", "B": "AS-101", "C": "LPC-100B", "D": "TMAC-102", "E": "LPC-204", "F": "TMAC-201", "G": "HB-101", "H": "TMAC-102"}
TIME_MAP = {"A": "01:50-03:15", "B": "12:15-01:40", "C": "09:35-11:00", "D": "08:00-09:25", \
            "E": "01:50-03:15", "F": "12:15-01:40", "G": "09:35-11:00", "H": "08:00-09:25"}

LETTERS = ["A", "B", "C", "D", "E", "F", "G", "H"]

with open('../data/id_table.json') as data_file:
    id_table = json.load(data_file)

def parse_classes(input):
    classes = []
    for k in range (0, len(LETTERS)):

        classname = ""
        try:
            i = input.index(LETTERS[k] + " - ")
            if LETTERS[k] != "H":
                classname = input[i + 4 : input.index(LETTERS[k + 1] + " -") - 1]
            else:
                classname = input[i + 4: -1]

            for person in id_table:
                if not person['gradyear']: # If they are a teacher
                    if person['lastname'] in classname:
                        classname = classname.replace(person['lastname'], '')

            classname = classname.replace('\n', '')
            classname = string.split(classname, 'Independent Study')[0]
            classname = string.split(classname, 'Seminars')[0]

            # Remove trailing whitespace
            classname = classname.rstrip()

        except ValueError:
            classname = "Free Period"

        classes.append({'name': classname, 'room': None, 'period': LETTERS[k], 'teacher': None})

    return classes

def get_id_object(sid):
    for item in id_table:
        if item['id'] == sid:
            return item

# Detect whether or not one or more duplicate classes (with the same name) occurs in a schedule
def duplicate_classes(classes):
    for i in range (0, len(classes)):
        for k in range (i + 1, len(classes)):
            if classes[i]['name'] == classes[i]['name']:
                return True

    return False

def is_period_free(classes, period):
    for clss in classes:
        if clss['period'] == period:
            if clss['name'] == 'Free Period':
                return True
            else:
                return False

def explode_pdf(path):
    path_properties = string.split(path, "/")  #Split the file name into a series of directories
    schedule_properties = string.split(path_properties[2], "-") #Extract the information from the name of the pdf

    #Turns the pdf into a list of pages of text boxes
    fp = file(path, 'rb')
    parser = PDFParser(fp)
    document = PDFDocument(parser, "")
    rsrcmgr = PDFResourceManager()
    laparams = LAParams()
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    classes = []  #Creates an 8 long list with a space for each class
    id_obj = get_id_object(int(schedule_properties[0]))
    period_letters = []
    duplicates = False
    schedule = {'firstname': id_obj['firstname'], 'lastname': id_obj['lastname'], \
        'username': id_obj['username'], 'sid': int(schedule_properties[0]), 'gradyear': None, 'grade': None}
        
    next_obj_is_advisor_name = 0

    for page in PDFPage.create_pages(document): #Run the following code on each page in the pdf
        interpreter.process_page(page)
        layout = device.get_result()
        if len(layout) == 0: #Weed out the blank pages
            continue

        for obj in layout:  #Run the following code on each object in the page

            if isinstance(obj, LTTextBox): #If the object is a text box

                contents = obj.get_text()
                #print "''" + contents + "'"

                # Check for letters
                if duplicates:
                    pieces = string.split(contents, "\n")
                    for letter in LETTERS:
                        for piece in pieces:
                            if len(piece) == 1 and letter in piece:
                                if not is_period_free(classes, letter):
                                    period_letters.append(letter)

                if "Block & Course" in contents:
                    classes = parse_classes(contents)
                    duplicates = duplicate_classes(classes)

                elif "Class of " in contents:
                    ageinfo = string.split(contents, "\n")

                    schedule["gradyear"] = int(ageinfo[0][ageinfo[0].index("Class of") + 9 : ageinfo[0].index("Class of") + 13])
                    schedule["grade"] = int(ageinfo[1][0 : ageinfo[1].index("th Grade")])

                elif next_obj_is_advisor_name > 0:
                    if next_obj_is_advisor_name == 2:
                        schedule["advisor_first"] = contents[0:contents.index("\n")].rstrip()
                    elif next_obj_is_advisor_name == 1:
                        schedule["advisor_last"] = contents[0:contents.index("\n")].rstrip()

                    next_obj_is_advisor_name -= 1

                elif "Advisor:" in contents and not "advisor_first" in schedule:
                    advisornames = string.split(contents, "\n")

                    if len(advisornames) < 3: # If this person has no locker number
                        next_obj_is_advisor_name = 2

                    else:
                        schedule["advisor_first"] = advisornames[1]
                        schedule["advisor_last"] = advisornames[2]

                elif "Middle Band Schedule" in contents:
                    break
                else:
                    # Parsing tables is difficult, so we will now scan each line
                    # to see what room each class is happening in
                    for clss in classes:
                        if clss['room'] or clss['name'] == "Free Period":
                            continue

                        # Otherwise, if we haven't figured out the room yet:
                        abbreviated = clss['name'][0:15]
                        contents = obj.get_text()

                        if abbreviated in contents and TIME_MAP[clss['period']] in contents:
                            clss['room'] = string.split(contents, "\n")[2]

    schedule['classes'] = classes
    return schedule

students = []
files = [f for f in os.listdir('..' + os.sep + 'schedules')] #Create a list of all files in the directory
for f in files:    #For each file in the directory
    #if f != "3283-1-18.pdf":
    #    continue
    if f in DO_NOT_PARSE: # If the schedule shouldn't be parsed
        print "Skipping"
        continue
    filepath = "../schedules/" + f   #Create the full filepath for the schedule
    print f

    if os.path.getsize(filepath) < 5000: # If schedule is blank (e.g. is less than 5000 bytes)
        print "Schedule is blank!"
        continue

    if f[-4:] == ".pdf":  #If the last 4 characters of the file name are .pdf (meaning the file is a schedule)
        exploded_schedule = explode_pdf(filepath)
        students.append(exploded_schedule)  #Add to the list of schedules the object returned by explode_pdf()

comment = """# Apply exceptions
EXCEPTIONS = {"4699": {"E": {"room": "TMAC-205A"}}, \
            "3283": {"B": {"room": "AX-107"}}, \
            "3283": {"C": {"room": "MS-203"}}}

for sid, exception in EXCEPTIONS.iteritems():
    # Find the person with that SID
    student = {}
    for s in students:
        if s['sid'] == int(sid):
            student = s

    if not student:
        continue
    
    for period, data in exception.iteritems():

        # Get correct period
        for clss in student['classes']:
            if clss['period'] == period:

                # Apply each property
                for prop, val in data.iteritems():
                    clss[prop] = val
                break
"""

print "Entering teacher names"

for person_num in range (0, len(students)):
    if students[person_num]['grade'] is not None: #If the person is a student
        for class_num in range (0, len(students[person_num]['classes'])): #For each class

            if students[person_num]['classes'][class_num]['name'] == 'Free Period':
                continue

            for teacher in students:
                if teacher['grade'] is None: # if the person is a teacher
                    # If the person is a teacher with the correct last names
                    if students[person_num]['classes'][class_num]['name'] == teacher['classes'][class_num]['name']:
                        # If the name, room, and period all line up, it's probably the same class, so we can set the teacher
                        students[person_num]['classes'][class_num]['teacher'] = teacher['firstname'] + " " + teacher['lastname']

    else: # If person is a teacher
        for class_num in range (0, len(students[person_num]['classes'])): #For each class

            if students[person_num]['classes'][class_num]['name'] == 'Free Period':
                continue

            for student in students:
                if student['grade'] is not None: # if the person is a student

                    if students[person_num]['classes'][class_num]['name'] == student['classes'][class_num]['name']:
                        # If the name, room, and period all line up, it's probably the same class, so we can set the room
                        students[person_num]['classes'][class_num]['room'] = student['classes'][class_num]['room']

# Get exceptions that still must be added
for student in students:
    if student['gradyear']: # If they are a student
        for clss in student['classes']:
            if clss['name'] != 'Free Period' and not clss['teacher']:
                print "SID " + str(student['sid']) + "(" + student['lastname'] + ", " + student['firstname'] + ") has no teacher for class " + clss['name']

file = open('../data/schedules.json', 'w')
file.write(json.dumps(students))