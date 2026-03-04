import argparse
import os
import time

from cron import photos, schedules, update_lunch

if __name__ == "__main__":
    # Set up Google Application Credentials if not already set
    if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service_account.json"

    # Parse command-line arguments
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
    parser.add_argument("--username", help="Specific username to update (for photos).")
    args = parser.parse_args()

    # Record start time for performance measurement
    start_time = time.time()
    print(
        f"Updating {args.data}... dry run={args.dry_run} "
        f"verbose={args.verbose} username={args.username}"
    )

    # Determine which function to call based on the data type
    callable_func = None
    if args.data == "lunches":
        callable_func = update_lunch.read_lunches
    elif args.data == "photos":
        callable_func = photos.crawl_photos
    elif args.data == "schedules":
        callable_func = schedules.crawl_schedules
    else:
        print("Invalid data type.")
        exit(1)

    # Call the appropriate function with the provided arguments
    if args.data == "photos":
        callable_func(args.dry_run, args.verbose, args.username)
    else:
        callable_func(args.dry_run, args.verbose)

    # Print the time taken for the operation
    print("Operation took {:.2f} seconds".format(time.time() - start_time))
