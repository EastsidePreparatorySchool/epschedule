# EPSchedule
A schedule app for Eastside Preparatory School, built with [Google App Engine](https://cloud.google.com/appengine) and [Polymer](https://polymer-project.org).

## Development

### Setup
- Install the [Google App Engine SDK for Python](https://cloud.google.com/appengine/downloads?hl=en)
- Install [NPM](https://www.npmjs.com/package/download)
- Install Bower 
```
npm install bower
```
- Install Grunt (for running tests)
```
npm install grunt
```

### Code style
We follow the Google [Python](https://google-styleguide.googlecode.com/svn/trunk/pyguide.html) and [JavaScript](https://google.github.io/styleguide/javascriptguide.xml) style guides.

### Running the app locally
From the main project directory, run
```
<path to app_engine_sdk>/dev_appserver.py .
```

### Running unit tests
From the main project directory, run
```
grunt runPythonTests
```

### Contributing a patch
From your fork of the epschedule repo, submit a pull request. Be sure that all tests pass, and you have followed the code style guides mentioned above.



