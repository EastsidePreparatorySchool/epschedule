import argparse
import os
import time

from cron import photos, schedules, update_lunch

if __name__ == "__main__":
    if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
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

    start_time = time.time()
    print(f"Updating {args.data}... dry run={args.dry_run} verbose={args.verbose}")
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
    print("Operation took {:.2f} seconds".format(time.time() - start_time))
