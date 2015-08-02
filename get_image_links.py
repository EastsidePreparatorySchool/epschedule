"""
This script's purpose is to use the website http://www.eastsideprep.org/who-we-are/biographies/
to generate a table of EPS staff members and their respective photos. This allows the software
to show photos of teachers in their respective classes and cards. This script shouldn't need any
updating, it will only need to be run from time to time as new teachers are added to EPS and other
teachers leave. However, if the EPS website is ever updated, this parser may no longer work,
meaning that it might need to be updated if that happens.
"""

#import json
import urllib
import urllib2
import string

images = [];
exceptions = [["(Tina)", "Hadden"], ["(Rikki)"]]

def checkText(text, character):
    for i in range (0, len(text)):
        if html[character + i] != text[i]:
            return False
    return True

response = urllib2.urlopen('http://www.eastsideprep.org/who-we-are/biographies/')
html = response.read()

for char in range (0, len(html)):
    if checkText("<img src='", char):
        char += 10
        imageurl = ""
        name = ""
        while (html[char] != "'"):
            imageurl += html[char]
            char += 1
        while not checkText("title='", char):
            char += 1
        char += 7
        while not checkText("'", char):
            name += html[char]
            char += 1
        images.append({"url":imageurl, "name":name})
        print imageurl
        print name

        name = name.split()
        name = name[1]
        name = name.lower()
        name += imageurl[len(imageurl) - 4:len(imageurl)] #Add on the extension
        while (True):
            try:
                urllib.urlretrieve(imageurl, "teacher_photos\\" + name)
                break
            except:
                print "Open connection was forcibly closed by a remote host, trying to download again"
#file = open('teacherimageurls.json', 'wb')
#file.write(json.dumps(images))