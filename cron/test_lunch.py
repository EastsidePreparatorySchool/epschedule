import datetime
from unittest.mock import patch

from cron.update_lunch import add_events

# Test reading lunch data from an ICS file and sanitizing it.
def test_read_lunches():
    events = []
    with patch(
        "cron.update_lunch.write_event_to_db", side_effect=lambda e: events.append(e)
    ) as mock:
        ICS_PATH = "data/test_lunch.ics"
        # Reads the ICS file to get a lunch object for 10/7/2019, Cheese Manicotti
        fake_response = open(ICS_PATH).read()
        add_events(fake_response)
        assert len(events) == 1
        event = events[0]
        assert event.summary == "Monday | Cheese Manicotti"
        assert event.day == datetime.date(2019, 10, 7)
