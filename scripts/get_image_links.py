"""
This script's purpose is to use the website http://www.eastsideprep.org/who-we-are/biographies/
to generate a table of EPS staff members and their respective photos. This allows the software
to show photos of teachers in their respective classes and cards. This script shouldn't need any
updating, it will only need to be run from time to time as new teachers are added to EPS and other
teachers leave. However, if the EPS website is ever updated, this parser may no longer work,
meaning that it might need to be updated if that happens.
"""

import urllib
import urllib2
import string
import sys
import json
import os

exceptions = { \
  "Ginger-Ellingson": "Virginia-Ellingson", \
  "Marcela-Winspear": "Marcela-Stepanova-Winspea", \
  "Nickie-Wallace": "Nicole-Wallace", \
  "randy-reina": "randall-randy-reina"
}

# Get a list of paragraphs from the entry-content div
def extract_paras(div):
    paras = []
    cursor = 0
    while True:
        para_start = div.find('<p>', cursor)
        if para_start == -1:
            break

        para_end = div.find('</p>', para_start)
        if para_end == -1:
            break

        para = div[para_start + 3:para_end]
        filter(lambda x: x in string.printable, para)
        paras.append(para)
        cursor = para_end + 4
    return paras

# Get a list of paragraphs from a HTML blob
def extract_bio(html):
    div_start = html.find('</p>', html.find('</em>'))
    if div_start == -1:
        print "Failed to find <div> start"
        return []

    div_end = html.find('</div>', div_start)
    if div_end == -1:
        print "Failed to find <div> end"
        return []

    div_content = html[div_start:div_end]
    return extract_paras(div_content)

def get_photo_and_bio(firstname, lastname):
    urlname = firstname + '-' + lastname

    if urlname in exceptions:
        urlname = exceptions[urlname]

    try:

        response = urllib2.urlopen('http://www.eastsideprep.org/faculty/' + firstname + '-' + lastname + '/')
        html = response.read()
    except:
        print "Failed to open page for " + firstname + ' ' + lastname + ", manual photo grabbing needed"
        return None

    imageurl = ""
    identifier = '"x-img"  src="'
    start = html.find(identifier) + len(identifier)

    for char in range(start, len(html)):
        if html[char] == '"':
            break
        else:
            imageurl += html[char]

    print "Found a URL, " + imageurl

    # Extract the bio from the HTML as an array of paragraphs
    bio = extract_bio(html)
    # Throw away the degree info paragraph
    cleaned_name = (firstname + "_" + lastname).lower()
    print "Extracted bio for " + lastname + " bio is " + str(bio)

    name = cleaned_name
    name += imageurl[len(imageurl) - 4:len(imageurl)] #Add on the extension
    while (True):
        try:
            urllib.urlretrieve(imageurl, "..\\teacher_photos\\" + name)
            break
        except:
            print "Open connection was forcibly closed by a remote host, trying to download again"

    print "Successfully downloaded image"
    return {'name':cleaned_name, 'bio':bio}






with open('../data/schedules.json') as data_file:
    id_table = json.load(data_file)

files = [f for f in os.listdir('..' + os.sep + 'teacher_photos')] #Create a list of all files in the directory

with open('../data/bios.json') as data_file:
    bios = json.load(data_file)

for teacher in id_table:
    if not teacher['gradyear']: # If they are a teacher

        # Test if they teach any classes
        teaches = False
        n = ""

        for clss in teacher['classes'][0]:
            if clss['name'] != "Free Period":
                n = clss['name']
                teaches = True
                break

        if not teaches:
            print teacher['firstname'] + " does not teach"
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
            print "Teacher " + teacher['lastname'] + " " + " teaches " + n
            print "Missing photo for " + teacher['firstname'] + " " + teacher['lastname']
            bio = get_photo_and_bio(teacher['firstname'], teacher['lastname'])
            if not bio:
                print "Could not download that photo, manual download needed"
            else:
                print "Obtained bio successfully"
            print "----------------"

print "Images downloaded, now cropping them"
writefile = open('../data/bios.json', 'wb')
writefile.write(json.dumps(bios))

comment = """

for mainchar in range (0, len(mainhtml)):
    if checkText("title='", mainchar, mainhtml):
        name = ""
        mainchar += 7
        while not checkText("'", mainchar, mainhtml):
            name += mainhtml[mainchar]
            mainchar += 1

        urlname = name.replace(" ", "-")
        urlname = urlname.replace("(", "")
        urlname = urlname.replace(")", "")

        for exception in exceptions:
            #print "Is " + exception[0] + " the same as " + urlname
            if exception[0] == urlname:
                urlname = exception[1]

        try:
            response = urllib2.urlopen('http://www.eastsideprep.org/team/' + urlname + '/')
            html = response.read()
        except:
            print "Failed to open page for " + urlname
            continue

        imageurl = "";
        for char in range (0, len(html)): #Find hd image url
            if checkText("post-thumbnail-link", char, html):
                while not checkText("src=\"", char, html):
                    char += 1
                char += 5
                while not checkText("\"", char, html):
                    imageurl += html[char]
                    char += 1

        # Extract the bio from the HTML as an array of paragraphs
        bio = extract_bio(html)
        # Throw away the degree info paragraph
        bio.pop(0)
        cleaned_name = name.replace(" ", "_")
        cleaned_name = cleaned_name.lower()
        bios.append({'name':cleaned_name, 'bio':bio})
        print "Extracted bio for " + urlname

        name = name.replace(" ", "_")
        name = name.lower()
        name += imageurl[len(imageurl) - 4:len(imageurl)] #Add on the extension
        while (True):
            try:
                urllib.urlretrieve(imageurl, "..\\teacher_photos\\" + name)
                break
            except:
                print "Open connection was forcibly closed by a remote host, trying to download again"

print "Images downloaded, now cropping them"
writefile = open('../data/bios.json', 'wb')
writefile.write(json.dumps(bios))
import create_teacher_icons #Runs create teacher icons
"""