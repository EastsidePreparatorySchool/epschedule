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

def convert_pdf_to_txt(path):
    rsrcmgr = PDFResourceManager()
    retstr = StringIO()
    codec = 'utf-8'
    laparams = LAParams()
    device = TextConverter(rsrcmgr, retstr, codec=codec, laparams=laparams)
    fp = file(path, 'rb')
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    password = ""
    maxpages = 0
    caching = True
    pagenos=set()
    for page in PDFPage.get_pages(fp, pagenos, maxpages=maxpages, password=password,caching=caching, check_extractable=True):
        interpreter.process_page(page)
    fp.close()
    device.close()
    str = retstr.getvalue()
    retstr.close()
    return str

def letterToNum(letter):#Converts a period into a list index
    letters = ["A", "B", "C", "D", "E", "F", "G", "H", "S", "V", "M", "L", "O"] #S - aSsembly, V - adVisory, M - class Meeting, L - cLubs and activities, O - Zero Period IME
    return letters.index(letter)

def graduating_year_to_grade(gy):
    date_obj = date.today()
    grade = 13 - (int(gy) - int(date_obj.year))
    if date_obj.month == 6:
        if date_obj.day >= 12:  #This could change
            grade -= 1
    elif date_obj.month > 6:
        grade -= 1
    return grade

def getClass(textbox):#Each textbox is passed in
    textboxlist = string.split(textbox, "\n")#Splits the textbox into lines
    if len(textboxlist) == 4:#All classes have a length of four lines. This throws away anything that isn't a class
        roomteacher = string.split(textboxlist[1], ": ")#Splits up the room and teacher into two different strings
        try:
            if (roomteacher[1] == "n/a"): #Assembly periods are also four lines. This weeds out assembly so it doesn't overwrite the A period class
                return None
        except:
            pass
        period = letterToNum(textboxlist[0][0])   #Takes the first character of the first line of the text box
        if len(roomteacher) == 1: #If the class has no teacher
            class_obj = {'name':textboxlist[2], 'room':roomteacher[0], 'teacher':"None", 'period':textboxlist[0][0]}
        else:
            class_obj = {'name':textboxlist[2], 'room':roomteacher[0], 'teacher':roomteacher[1], 'period':textboxlist[0][0]}#Shoves all the information into a object
        return {'period_num':period, 'class':class_obj }#Returns an object containing the class info and the period info
    #elif len(textboxlist) = 3:
    #    if
    else:
        return None


def explode_pdf(path):
    path_properties = string.split(path, "\\")  #Split the file name into a series of directories
    schedule_properties = string.split(path_properties[7], "-") #Extract the information from the name of the pdf
    if len(schedule_properties) > 4: #If the person has a dash in their last name
        schedule_properties[2] += "-" + schedule_properties[3]
        schedule_properties[3] = schedule_properties[4]

    #Turns the pdf into a list of pages of text boxes
    fp = file(path, 'rb')
    parser = PDFParser(fp)
    document = PDFDocument(parser, "")
    rsrcmgr = PDFResourceManager()
    laparams = LAParams()
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    advisor_first = None
    advisor_last = None
    grade = None
    ##################################################
    classes = []  #Creates an 8 long list with a space for each class
    for page in PDFPage.create_pages(document): #Run the following code on each page in the pdf
        interpreter.process_page(page)
        layout = device.get_result()
        if len(layout) == 0: #Weed out the blank pages
            continue
        for obj in layout:  #Run the following code on each object in the page
          if isinstance(obj, LTTextBox):    #If the object is a text box
            class_obj = getClass(obj.get_text())    #Extract the information from the text box
            info = string.split(obj.get_text(), "|")
            if class_obj != None:   #If getClass() didn't return an error
                #print classes
                #print class_obj["period_num"]
                classes.append(class_obj['class'])  #Shove the information passed back from getClass() into it's appropriate space in the list
            elif len(info) == 4: #If the obj contains information on the user's name, advisor, grade, and locker num
                graduating_year = info[1][-5:-1]
                grade = graduating_year_to_grade(graduating_year)
                advisor = info[2][10:-1]
                advisor_names = string.split(advisor, ", ")
                advisor_first = advisor_names[1]
                advisor_last = advisor_names[0]
    device.close()

    if classes == []: #If the schedule is blank or not a schedule
        return None
    cleaned_classes = [] #Remove duplicates from classes
    for l in classes:
        if l not in cleaned_classes:
            cleaned_classes.append(l)

    schedule_properties[3] = schedule_properties[3][:-4] #Remove the .pdf extention
    schedule_obj = {'firstname':schedule_properties[3], 'lastname':schedule_properties[2], 'term':schedule_properties[1], 'id':schedule_properties[0], 'grade':grade, 'advisorfirstname':advisor_first, 'advisorlastname':advisor_last, 'classes':cleaned_classes}
    return schedule_obj    #Return object created in the previous line

def add_free_periods(schedule_obj):
    periods = ["A", "B", "C", "D", "E", "F", "G", "H"]
    for class_obj in schedule_obj['classes']:
        if periods.count(class_obj['period']):
            periods.remove(class_obj['period'])

    for period in periods:
        schedule_obj['classes'].append({'period':period, 'teacher':"", 'room':"", 'name':"Free Period"})

    return schedule_obj
#print convert_pdf_to_txt("c:\\users\\guberti\\Documents\\My Projects\\Python\\Schedule Downloader\\4093-3-Uberti-Gavin.pdf")
students = []
files = [f for f in os.listdir('..' + os.sep + 'schedules')]#Create a list of all files in the directory
for f in files:    #For each file in the directory
    if f in DO_NOT_PARSE: # If the schedule shouldn't be parsed
        print "Error"
        continue
    if f[len(f) - 4:len(f)] == ".pdf":  #If the last 4 characters of the file name are .pdf (meaning the file is a schedule)
        filepath = "c:\\users\\guberti\\Documents\\Github\\EPSchedule\\schedules\\" + f   #Create the full filepath for the schedule
        #print filepath
        print f
        exploded_schedule = explode_pdf(filepath)
        if exploded_schedule is not None: #If exploded_schedule is not none
            exploded_schedule = add_free_periods(exploded_schedule)
            students.append(exploded_schedule)  #Add to the list of schedules the object returned by explode_pdf()
        else:
            print "Schedule is empty!"

print "Entering full names!"
for person_num in range (0, len(students)):
    if students[person_num]['grade'] is not None: #If the person is a students
        for class_num in range (0, len(students[person_num]['classes'])): #For each class
            for teacher in students:
                if teacher['grade'] is None: #If the person is a teacher
                    for taught_class in teacher['classes']:
                        if students[person_num]['classes'][class_num]['period'] == taught_class['period'] and students[person_num]['classes'][class_num]['room'] == taught_class['room'] and students[person_num]['classes'][class_num]['name'] == taught_class['name']:
                            students[person_num]['classes'][class_num]['teacher'] = teacher['firstname'] + " " + teacher['lastname']

file = open('..\\schedules.json', 'w')
file.write(json.dumps(students))
#print students  #Print the list of schedules