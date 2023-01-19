import argparse
import os

from cron import photos, schedules, update_lunch

if __name__ == "__main__":
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service_account.json"
    parser = argparse.ArgumentParser()
    parser.add_argument("data", help="Which data update.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="If set, the results are not uploaded to production.",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Print debugging output."
    )
    args = parser.parse_args()

    callable = None
    if args.data == "lunches":
        callable = update_lunch.read_lunches
    elif args.data == "photos":
        callable = photos.crawl_photos
    elif args.data == "schedules":
        callable = schedules.crawl_schedules
    else:
        print("Invalid data type.")
        exit(1)

    callable(args.dry_run, args.verbose)
