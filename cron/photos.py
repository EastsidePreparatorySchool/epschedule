import hashlib
import hmac
import json
import os
import time
from io import BytesIO

import PIL
import requests
from google.cloud import secretmanager, storage
from PIL import Image

ICON_SIZE = 96  # 96x96 pixels
SECRET_REQUEST = {"name": "projects/epschedule-v2/secrets/four11_key/versions/1"}


def download_photo_bytes(url):
    req = requests.get(url, stream=True)
    return Image.open(BytesIO(req.content))


def download_photo(user):
    photo_url = "http://four11.eastsideprep.org/system/"
    if user["grade"]:
        photo_url += "students"
    else:
        photo_url += "teachers"
    photo_url += "/idphotos/000/00"

    sid = str(user["sid"])

    if len(sid) == 3:
        photo_url += "0/" + sid
    else:  # If length is 4
        photo_url += sid[0] + "/" + sid[1:]

    photo_url += "/medium/"

    last = user["lastname"].replace(" ", "_").replace(".", "")
    first = user["firstname"].replace(" ", "_").replace(".", "")

    primary_url = photo_url + last + "__" + first + ".jpg"
    backup_url = photo_url + last + "_" + first + "_" + sid + ".jpg"

    # Now try each url - I'm unsure why we sometimes need to fall back to
    # the secondary URL, but it is necessary
    try:
        return download_photo_bytes(primary_url)
    except PIL.UnidentifiedImageError:
        print("Unable to download {} with primary url".format(user["username"]))
    try:
        return download_photo_bytes(backup_url)
    except PIL.UnidentifiedImageError:
        print("UNABLE to download " + user["username"])
        # Some students don't have photos if they never went for picture day
    return None


def crop_image(img):
    if img.width > img.height:
        img = img.resize(((ICON_SIZE * img.width) // img.height, ICON_SIZE))
        border = (img.width - ICON_SIZE) / 2
        cropparams = (border, 0)
    else:
        img = img.resize((ICON_SIZE, (ICON_SIZE * img.height) // img.width))
        border = (img.height - ICON_SIZE) // 2
        cropparams = (0, border)
    return img.crop(
        (*cropparams, img.width - cropparams[0], img.height - cropparams[1]))


def hash_username(key, username, icon=False):
    if icon:
        username += "-icon"
    hashed = hmac.new(key, username.encode("utf-8"), hashlib.sha256)
    return hashed.hexdigest() + ".jpg"


def upload_photo(bucket, filename, photo):
    with BytesIO() as output:
        photo.save(output, format="JPEG")
        bucket.blob(filename).upload_from_string(output.getvalue())
        print(bucket.blob(filename).public_url)


# Takes about three minutes for ~450 photos
def crawl_photos():
    # Prepare our secret
    start = time.time()
    secret_client = secretmanager.SecretManagerServiceClient()
    secret_response = secret_client.access_secret_version(request=SECRET_REQUEST)
    key = secret_response.payload.data.decode('UTF-8')

    # Open the bucket
    storage_client = storage.Client()
    avatar_bucket = storage_client.bucket("epschedule-avatars")
    data_bucket = storage_client.bucket("epschedule-data")
    schedule_blob = data_bucket.blob("schedules.json")
    schedules = json.loads(schedule_blob.download_as_string())

    for schedule in schedules:
        photo = download_photo(schedule)
        if photo is None:
            continue
        fullsize_filename = hash_username(key, schedule["username"])
        upload_photo(avatar_bucket, fullsize_filename, photo)

        # Now crop photo
        cropped = crop_image(photo)
        icon_filename = hash_username(key, schedule["username"], icon=True)
        upload_photo(avatar_bucket, icon_filename, cropped)

        # For teachers, upload an unhashed grayscale photo
        if not schedule["grade"]:
            grayscale = cropped.convert("L")
            upload_photo(avatar_bucket, schedule["username"] + ".jpg", grayscale)

    print("Operation took {:.2f} seconds".format(time.time() - start))


if __name__ == "__main__":
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "../service_account.json"
    crawl_photos()
