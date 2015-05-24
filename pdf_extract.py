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
    letters = ["A", "B", "C", "D", "E", "F", "G", "H", "S", "V", "M", "L"] #S - aSsembly, V - adVisory, M - class Meeting, L - cLubs and activities
    return letters.index(letter)

def getClass(textbox):#Each textbox is passed in
    textboxlist = string.split(textbox, "\n")#Splits the textbox into lines
    if len(textboxlist) == 4:#All classes have a length of four lines. This throws away anything that isn't a class
        roomteacher = string.split(textboxlist[1], ": ")#Splits up the room and teacher into two different strings
        if (roomteacher[1] == "n/a"):#Assembly periods are also four lines. This weeds out assembly so it doesn't overwrite the A period class
            period = 8
            class_obj = {'name': textboxlist[2], 'room':roomteacher[0], 'teacher': "N/A", 'period': "S"}
            return {'period_num':period, 'class':class_obj }
        period = letterToNum(textboxlist[0][0])#Takes the first character of the first line of the text box
        class_obj = {'name':textboxlist[2], 'room':roomteacher[0], 'teacher':roomteacher[1], 'period':textboxlist[0][0]}#Shoves all the information into a object
        return {'period_num':period, 'class':class_obj }#Returns an object containing the class info and the period info
    elif len(textboxlist) = 3:
        if 
    else:
        return None
    

def explode_pdf(path):
    #Turns the pdf into a list of pages of text boxes
    fp = file(path, 'rb')
    parser = PDFParser(fp)
    document = PDFDocument(parser, "")
    rsrcmgr = PDFResourceManager()
    laparams = LAParams()
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    ##################################################
    classes = ["", "", "", "", "", "", "", ""]  #Creates an 8 long list with a space for each class
    for page in PDFPage.create_pages(document): #Run the following code on each page in the pdf
        interpreter.process_page(page)
        layout = device.get_result()
        for obj in layout:  #Run the following code on each object in the page
          if isinstance(obj, LTTextBox):    #If the object is a text box
            class_obj = getClass(obj.get_text())    #Extract the information from the text box
            if class_obj != None:   #If getClass() didn't return an error
                classes[class_obj['period_num']] = class_obj['class']   #Shove the information passed back from getClass() into it's appropriate space in the list
    device.close()
    path_properties = string.split(path, "\\")  #Split the file name into a series of directories
    schedule_properties = string.split(path_properties[8], "-") #Extract the information from the name of the pdf
    schedule_obj = {'firstname':schedule_properties[3], 'lastname':schedule_properties[2], 'term':schedule_properties[1], 'id':schedule_properties[0], 'classes':classes}
    return schedule_obj    #Return object created in the previous line
    
#print convert_pdf_to_txt("c:\\users\\guberti\\Documents\\My Projects\\Python\\Schedule Downloader\\4093-3-Uberti-Gavin.pdf")
students = []
files = [f for f in os.listdir('.' + os.sep + 'schedules')]#Create a list of all files in the directory
for f in files:    #For each file in the directory
    if f[len(f) - 4:len(f)] == ".pdf":  #If the last 4 characters of the file name are .pdf (meaning the file is a schedule)
        filepath = "c:\\users\\guberti\\Documents\\My Projects\\App Engine\\epschedule\\schedules\\" + f   #Create the full filepath for the schedule
        students.append(explode_pdf(filepath))  #Add to the list of schedules the object returned by explode_pdf()

file = open('schedules.json', 'wb')
file.write(json.dumps(students))
print students  #Print the list of schedules