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
import sys
import json

exceptions = [ \
  ["Ginger-Ellingson", "Virginia-Ellingson"], \
  ["Marcela-Winspear", "Marcela-Stepanova-Winspea"], \
  ["Nickie-Wallace", "Nicole-Wallace"] \
]

def checkText(text, character, textblock):
    for i in range (0, len(text)):
        if textblock[character + i] != text[i]:
            return False
    return True

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
    div_start = html.find('<div class="entry-content">')
    if div_start == -1:
        print "Failed to find <div> start"
        return []

    div_end = html.find('</div><!-- .entry-content -->', div_start)
    if div_end == -1:
        print "Failed to find <div> end"
        return []

    div_content = html[div_start:div_end]
    return extract_paras(div_content)

bios = []
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
