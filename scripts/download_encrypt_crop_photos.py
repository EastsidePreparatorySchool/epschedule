import json
import urllib2
from Crypto.Hash import SHA256
from wand.image import Image
import os
import base64
import shutil
import datetime


with open('../data/schedules.json') as data_file:
    SCHEDULES = json.load(data_file)

with open('../data/crypto.key') as key:
    CRYPTO_KEY = key.read().strip()

# Returns current school year string, i.e. "19-20"
def current_school_year_string():
    now = datetime.datetime.now()
    start_year = now.year % 100
    if now.month <= 6:
        start_year -= 1
    return str(start_year) + "-" + str(start_year + 1)

def download_photo(url, path):
    resp = urllib2.urlopen(url).read()
    with open(path, 'wb') as f:
        f.write(resp)

def download_cleartext_photos(folder):
    for student in SCHEDULES:
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

        last = student["lastname"].replace(" ", "_").replace(".", "")
        first = student["firstname"].replace(" ", "_").replace(".", "")

        primary_url = photo_url + last + "__" + first + ".jpg"
        backup_url = photo_url + last + "_" + first + "_" + sid + ".jpg"

        filepath = folder + "/" + student["username"] + ".jpg"
        print "Downloaded " + photo_url + " to " + filepath

        # Now try each url
        try:
            download_photo(primary_url, filepath)
            print("Downloaded " + student["username"] + " with primary url")
            continue
        except urllib2.HTTPError:
            print("Received an error")
        try:
            download_photo(backup_url, filepath)
            print("Downloaded " + student["username"] + " with BACKUP url")
            continue
        except urllib2.HTTPError:
            print("Received an error")
        print("UNABLE to download " + student["username"])

    print("Downloaded " + str(len(SCHEDULES)) + " photos")

CROP_SIDE = 96

def crop_folder(input_dir, output_dir, grayscale=False, restrict_teachers=False):
    for image in os.listdir(input_dir):
        full_path = os.path.join(input_dir, image)
        if not os.path.isfile(full_path):
            continue

        if restrict_teachers and next(
            (x for x in SCHEDULES if x['username'] == image[:-4]))['grade']:
            continue


        print "Cropping " + str(image)
        with Image(filename=full_path) as img:
            if (img.width > img.height):
                img.resize((CROP_SIDE * img.width) / img.height, CROP_SIDE)
                border = (img.width - CROP_SIDE) / 2
                cropparams = [border, 0]
            else:
                img.resize(CROP_SIDE, (CROP_SIDE * img.height) / img.width)
                border = (img.height - CROP_SIDE) / 2
                cropparams = [0, border]

            img.crop(cropparams[0], cropparams[1], img.width - cropparams[0], img.height - cropparams[1])
            if grayscale:
                img.type = 'grayscale'
            img.convert('jpeg')

            img.save(filename=os.path.join(output_dir, os.path.splitext(image)[0] + '.jpg'))

def copy_encrypt_photos(input_dir, output_dir):
    for filename in os.listdir(input_dir):
        if os.path.isdir(input_dir + filename):
            continue

        hasher_input = filename[:-4]

        hasher = SHA256.new(CRYPTO_KEY)
        hasher.update(hasher_input)
        hashed = hasher.hexdigest()

        print filename + " --> " + hashed

        shutil.copyfile(os.path.join(input_dir, filename), os.path.join(output_dir, hashed + ".jpg"))

# Keeps directories intact
def empty_folder(folder):
    removed = 0
    for image in os.listdir(folder):
        full_path = os.path.join(folder, image)
        if os.path.isfile(full_path):
            os.remove(full_path)
            removed += 1

    if removed > 0:
        print("Removed " + str(removed) + " from " + folder)

SCHOOL_YEAR = current_school_year_string()

ENCRYPTED_FOLDER = "../school_photos"
CLEARTEXT_FOLDER = ENCRYPTED_FOLDER + "/" + SCHOOL_YEAR
THUMBNAIL_FOLDER = "../96x96_photos"

# First empty needed directories
if os.path.exists(CLEARTEXT_FOLDER):
    empty_folder(CLEARTEXT_FOLDER)
    print("Used existing directory " + CLEARTEXT_FOLDER)
else:
    os.mkdir(CLEARTEXT_FOLDER)
    print("Made new directory " + CLEARTEXT_FOLDER)

empty_folder(ENCRYPTED_FOLDER)
empty_folder(THUMBNAIL_FOLDER)
print("Emptied " + ENCRYPTED_FOLDER + " and " + THUMBNAIL_FOLDER)

# Now we'll download all photos
download_cleartext_photos(CLEARTEXT_FOLDER)

# Encrypt and copy all photos to fullsize and thumbnails
copy_encrypt_photos(CLEARTEXT_FOLDER, ENCRYPTED_FOLDER)
crop_folder(ENCRYPTED_FOLDER, THUMBNAIL_FOLDER)

# Do BW cleartext crops on teacher images
crop_folder(CLEARTEXT_FOLDER, THUMBNAIL_FOLDER, grayscale=True, restrict_teachers=True)
