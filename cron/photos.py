import hashlib
import hmac
from io import BytesIO

import PIL
import requests
from google.cloud import secretmanager, storage
from PIL import Image

from cron import four11

SECRET_REQUEST = {"name": "projects/epschedule-v2/secrets/session_key/versions/1"}
ICON_SIZE = 96,96  # 96x96 pixels. For Gavin's past code, use ICON_SIZE = 96


def download_photo_from_url(session, url):
    # try to get the photo from a given URL
    try:
        response = session.get(url)
        # open the image in the response given
        return Image.open(BytesIO(response.content))
    except PIL.UnidentifiedImageError:
        # if there is an error, just return none
        return None


def crop_image(img):
    # past code by Gavin 
    # if img.width > img.height:
    #     img = img.resize(((ICON_SIZE * img.width) // img.height, ICON_SIZE))
    #     border = (img.width - ICON_SIZE) / 2
    #     cropparams = (border, 0)
    # else:
    #     img = img.resize((ICON_SIZE, (ICON_SIZE * img.height) // img.width))
    #     border = (img.height - ICON_SIZE) // 2
    #     cropparams = (0, border)
    # return img.crop(
    #     (*cropparams, img.width - cropparams[0], img.height - cropparams[1])
    # )

    # copies the image
    copy = img.copy()
    # grabs its thumbnail according to ICON SIZE
    copy.thumbnail(ICON_SIZE)
    # returns the thumbnail
    return copy


def hash_username(key, username, icon=False):
    # if its an icon, name it as such
    if icon:
        username += "-icon"
    # hash the new name of the image
    hashed = hmac.new(key, username.encode("utf-8"), hashlib.sha256)
    # return the hashed item with JPG file extension
    return hashed.hexdigest() + ".jpg"


def upload_photo(bucket, filename, photo, verbose=False):
    # output to bytes
    with BytesIO() as output:
        # save it in there as JPEG
        photo.save(output, format="JPEG")
        # read in value from the bytesio, then upload it to the bucket
        bucket.blob(filename).upload_from_string(output.getvalue())
        if verbose:
            # if verbose, print the URL to the current file
            print(bucket.blob(filename).public_url)


# Takes about three minutes for ~450 photos
# crawls all the photos from four11 and adds it to the EPSchedule bucket
# run with dry_run=True if this is just a test and you don't want to actually upload
# run with verbose=True if you want to see what's going on (90% of the time do this)
def crawl_photos(dry_run=False, verbose=False):
    # establishes clients for four11, secret manager
    four11_client = four11.Four11Client()
    secret_client = secretmanager.SecretManagerServiceClient()
    # requests secrets from secret manager
    key_bytes = secret_client.access_secret_version(request=SECRET_REQUEST).payload.data

    # set up the system with sessions, clients, and lists
    session = requests.Session() #open a session
    storage_client = storage.Client() #open a storage client
    avatar_bucket = storage_client.bucket("epschedule-avatars") #find the bucket from there
    people = four11_client.get_people() #get the list of people from four11

    # for each person
    for user in people:
        photo_url = user.photo_url # grab their photo URL
        username = user.username() # grab their username
        photo = download_photo_from_url(session, photo_url) # download their photo from said url

        if photo is None: # if they don't have a photo
            # error message
            print(f"Unable to download photo for user {username} from {photo_url}")
            continue #skip to next person
        if photo.width > photo.height: # if photo is in landscape mode
            # mention that
            print(
                f"Image for user {username} from {photo_url} is landscape, {photo.width}x{photo.height}"
            )

        # hash the file name
        fullsize_filename = hash_username(key_bytes, username)
        if not dry_run: # if its not a test run
            # upload the photo
            upload_photo(avatar_bucket, fullsize_filename, photo)

        # Now crop photo
        photo.save("person_photo.jpeg", "JPEG") #save it as JPEG in placeholder
        cropped = crop_image(photo) #crop it using the function
        cropped.save("person_thumbnail.jpeg", "JPEG") #save the cropped image
        icon_filename = hash_username(key_bytes, username, icon=True) #save the icon file name
        if not dry_run: # if its not a test run
            # upload the photo
            upload_photo(avatar_bucket, icon_filename, cropped)

        # For teachers, upload an unhashed grayscale photo for class 
        if user.is_staff(): # if its a teacher
            grayscale = cropped.convert("L") #uses pillow to map to grayscale
            if not dry_run: # if its not a test run
                # upload the photo
                upload_photo(avatar_bucket, username + ".jpg", grayscale)

        if verbose: # if you want to see whats happening
            # note that this person was just processed
            print(f"Processed photo for user {username}")

