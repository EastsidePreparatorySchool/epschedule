import json
import os
import sys

from google.cloud import storage

# For simplicity, this script uses relative paths
# Thus, it must be run from the scripts folder
DIRNAME = os.path.dirname(__file__)
MASTER_SCHEDULE_PATH = os.path.join(DIRNAME, "../data/master_schedule.json")
CREDS_PATH = os.path.join(DIRNAME, "../service_account.json")


def upload_master_schedule():
    # Open the bucket
    storage_client = storage.Client()
    data_bucket = storage_client.bucket("epschedule-data")

    # Sanity check to make sure exceptions.json is valid
    with open(MASTER_SCHEDULE_PATH) as file:
        try:
            data = json.load(file)
        except json.decoder.JSONDecodeError:
            print("master_schedule.json is invalid, cancelling upload")
            sys.exit(1)

    # Upload the file
    schedule_blob = data_bucket.blob("master_schedule.json")
    schedule_blob.upload_from_filename(MASTER_SCHEDULE_PATH)


if __name__ == "__main__":
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDS_PATH
    upload_master_schedule()
