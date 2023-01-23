import hashlib
import hmac
import time
from io import BytesIO

import PIL
import requests
from google.cloud import storage
from PIL import Image

from cron import four11

ICON_SIZE = 96  # 96x96 pixels


def download_photo_from_url(session, url):
    try:
        response = session.get(url)
        return Image.open(BytesIO(response.content))
    except PIL.UnidentifiedImageError:
        print(f"Unable to download image at {url}")
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
        (*cropparams, img.width - cropparams[0], img.height - cropparams[1])
    )


def hash_username(key, username, icon=False):
    if icon:
        username += "-icon"
    hashed = hmac.new(key, username.encode("utf-8"), hashlib.sha256)
    return hashed.hexdigest() + ".jpg"


def upload_photo(bucket, filename, photo, verbose=False):
    with BytesIO() as output:
        photo.save(output, format="JPEG")
        bucket.blob(filename).upload_from_string(output.getvalue())
        if verbose:
            print(bucket.blob(filename).public_url)


# Takes about three minutes for ~450 photos
def crawl_photos(dry_run=False, verbose=False):
    start = time.time()
    four11_client = four11.Four11Client()
    key_bytes = four11_client.api_key().encode("utf-8")

    # Open the bucket
    session = requests.Session()
    storage_client = storage.Client()
    avatar_bucket = storage_client.bucket("epschedule-avatars")
    people = four11_client.get_people()

    for user in people:
        photo = download_photo_from_url(session, photo_url)
        if photo is None:
            continue

        fullsize_filename = hash_username(key_bytes, username)
        if not dry_run:
            upload_photo(avatar_bucket, fullsize_filename, photo)

        # Now crop photo
        cropped = crop_image(photo)
        icon_filename = hash_username(key_bytes, username, icon=True)
        if not dry_run:
            upload_photo(avatar_bucket, icon_filename, cropped)

        # For teachers, upload an unhashed grayscale photo
        if user.is_staff():
            grayscale = cropped.convert("L")
            if not dry_run:
                upload_photo(avatar_bucket, username + ".jpg", grayscale)
        if verbose:
            print(f"Processed photo for user {username}")

    print("Operation took {:.2f} seconds".format(time.time() - start))
