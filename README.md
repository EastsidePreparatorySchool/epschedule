<h1 align="center">EPSchedule</h2>

<p align="center">
<a href="https://github.com/guberti/epschedule/actions"><img alt="Test Status" src="https://github.com/guberti/epschedule/workflows/tests/badge.svg?branch=master"></a>
<a href="https://stats.uptimerobot.com/6m9K2UoPpz"><img alt="Uptime Robot ratio (30 days)" src="https://img.shields.io/uptimerobot/ratio/m783284473-f52bd1a250d8d4f68453f24d"></a>
<a href="https://github.com/guberti/epschedule/blob/master/LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg"></a>
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
</p>

A schedule app for Eastside Preparatory School, built with [Google App Engine](https://cloud.google.com/appengine) and [Polymer](https://polymer-project.org).

## Running EPSchedule locally

EPSchedule is designed to be *extremely* easy to get running locally - all you need are `git` and Python 3.7+. To set it up, just run:

```
git clone https://github.com/guberti/epschedule.git
cd epschedule
pip install -r requirements.txt
```

You'll then need to get service account credentials to access sensitive user data, like schedules, photos, and crypto keys. Email Mr. Briggs or Gavin Uberti (gavin.uberti@gmail.com) and we'll send you a file - `epschedule-455d8a10f5ec.json` - to put in your `epschedule` folder. Then, just run

```python main.py```

and navigate to http://localhost:8080/, where a local version of EPSchedule will be running!

## Development

### Code style
We try to follow the Google [Python](https://google-styleguide.googlecode.com/svn/trunk/pyguide.html) and [JavaScript](https://google.github.io/styleguide/javascriptguide.xml) style guides.

### Contributing a patch
From your fork of the epschedule repo, submit a pull request. Be sure that all tests pass, and you have followed the code style guides mentioned above.

### Getting the schedule from 411 into Epschedule
Under Scripts in the epschedule folder, simply click on the date_schedule.py application. This will put all of the current data about the schedules for certain days into the master_schedule.json document. Committing this to Github will finalize the changes (and put them into google cloud).
