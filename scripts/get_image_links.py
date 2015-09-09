"""
This script's purpose is to use the website http://www.eastsideprep.org/who-we-are/biographies/
to generate a table of EPS staff members and their respective photos. This allows the software
to show photos of teachers in their respective classes and cards. This script shouldn't need any
updating, it will only need to be run from time to time as new teachers are added to EPS and other
teachers leave. However, if the EPS website is ever updated, this parser may no longer work,
meaning that it might need to be updatingated if that happens.
"""

#import json
import urllib
import urllib2
import string
import sys
import json

exceptions = [["Ginger-Ellingson", "Virginia-Ellingson"], ["Marcela-Winspear", "Marcela-Stepanova-Winspea"], ["Nickie-Wallace", "Nicole-Wallace"]]
bios = []
def checkText(text, character, textblock):
    for i in range (0, len(text)):
        if textblock[character + i] != text[i]:
            return False
    return True

mainresponse = urllib2.urlopen('http://www.eastsideprep.org/who-we-are/biographies/')
mainhtml = mainresponse.read()

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

            response = urllib2.urlopen('http://www.eastsideprep.org/team/' + urlname + '/')
            html = response.read()
            imageurl = "";
            for char in range (0, len(html)): #Find hd image url
                if checkText("post-thumbnail-link", char, html):
                    while not checkText("src=\"", char, html):
                        char += 1
                    char += 5
                    while not checkText("\"", char, html):
                        imageurl += html[char]
                        char += 1
            pTags = 0
            char = 0
            bio = ""
            for char in range (0, len(html)):
                if checkText("<p>", char, html):
                    if (pTags >= 1):
                        char += 3
                        while True:
                            if checkText("</p>", char, html):
                                break
                            bio += html[char]
                            char += 1

                    else:
                        pTags += 1
            filter(lambda x: x in string.printable, bio)
            cleaned_name = name.replace(" ", "_")
            cleaned_name = cleaned_name.lower()
            bios.append({'name':cleaned_name, 'bio':bio})
            print imageurl
            print name

            name = name.replace(" ", "_")
            name = name.replace("-", "_")
            name = name.lower()
            name += imageurl[len(imageurl) - 4:len(imageurl)] #Add on the extension
            #while (True):
            #    try:
            #        urllib.urlretrieve(imageurl, "..\\teacher_photos\\" + name)
            #        break
            #    except:
            #        print "Open connection was forcibly closed by a remote host, trying to download again"
print "Images downloaded, now cropping them"
writefile = open('../bios.json', 'wb')
writefile.write(json.dumps(bios))
#import create_teacher_icons #Runs create teacher icons