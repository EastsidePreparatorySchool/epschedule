<h1 align="center">EPSchedule</h2>

<p align="center">
<a href="https://github.com/guberti/epschedule/actions"><img alt="Test Status" src="https://github.com/guberti/epschedule/workflows/tests/badge.svg?branch=master"></a>
<a href="https://stats.uptimerobot.com/6m9K2UoPpz"><img alt="Uptime Robot ratio (30 days)" src="https://img.shields.io/uptimerobot/ratio/m783284473-f52bd1a250d8d4f68453f24d"></a>
<a href="https://github.com/guberti/epschedule/blob/master/LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg"></a>
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
</p>

A schedule app for Eastside Preparatory School, built with [Google App Engine](https://cloud.google.com/appengine) and [Polymer](https://polymer-project.org).

## Running EPSchedule locally

EPSchedule is designed to be *extremely* easy to get running locally - all you need are `git`, Python 3.7+, and `pip`. To set it up, just run:

```
git clone https://github.com/guberti/epschedule.git
cd epschedule
pip install -r requirements.txt
```

You'll then need to get service account credentials to access sensitive user data, like schedules, photos, and crypto keys. Email Kalie Uberti (kalie.c.uberti@gmail.com) and we'll send you a file - `epschedule-v2-xxxx.json` - which should be renamed to `service_account.json` and put in your `epschedule` folder. Then, just run

```python main.py```

and navigate to http://localhost:8080/, where a local version of EPSchedule will be running!

## Development

### Code style
We try to follow the Black [Python](https://black.readthedocs.io/en/stable/the_black_code_style/current_style.html) and Google [JavaScript](https://google.github.io/styleguide/javascriptguide.xml) style guides. To auto-format your Python code, run

```
black .
isort . --profile black
```

from the command line.

### Running unit tests
We use the [pytest](https://docs.pytest.org/en/stable/index.html) framework to test our Python code, and tests are run against all pull requests. To run the tests locally, simply run 

```pytest```

from the command line.

### Contributing a patch
From your fork of the epschedule repo, submit a pull request. Be sure that all tests pass, and you have followed the code style guides mentioned above.

### Updating the master schedule
To recrawl or manually adjust the master period schedule (master_schedule.json), follow the instructions at [this link](https://github.com/guberti/epschedule/wiki/How-to-Crawl-schedules).

### More details
For more details, see the EPSchedule [wiki](https://github.com/guberti/epschedule/wiki).

