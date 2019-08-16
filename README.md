<h1 align="center">EPSchedule</h2>

<p align="center">
<a href="https://travis-ci.com/guberti/epschedule"><img alt="Build Status" src="https://travis-ci.org/guberti/epschedule.svg?branch=master"></a>
<img alt="Uptime Robot ratio (30 days)" src="https://img.shields.io/uptimerobot/ratio/m783284473-f52bd1a250d8d4f68453f24d">
<a href="https://github.com/guberti/epschedule/blob/master/LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg"></a>
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
</p>

A schedule app for Eastside Preparatory School, built with [Google App Engine](https://cloud.google.com/appengine) and [Polymer](https://polymer-project.org).

## Installing development tools on Windows

### Git setup
As you've probably already guessed, EPSchedule uses git for version control. To test if you have git installed, open a command prompt window and type `git`. If the command isn't recognized, you should [install GitHub Desktop](https://desktop.github.com/) which includes git.

Once git is installed, open a **new** command prompt and navigate to the directory you'd like to build EPSchedule from. If you don't know where this is, just type `cd %HOMEPATH%/Documents/Github` in the command prompt to navigate to `C:/Users/guberti/Documents/Github` (if this path doesn't already exist, you may need to create it).

Now clone the repository by running `git clone https://github.com/guberti/epschedule.git`.

Congrats! You now have the EPSchedule codebase on your computer!

### Python 2.7
EPSchedule's backend code is written for Google App Engine with Python 2. We'll need to install it to run EPSchedule locally.

If you don't already have Python 2 on your computer, (download the latest version)[https://www.python.org/downloads/release/python-2716/] from the Python website (you'll want the `Windows x86 MSI` installer). Install it to the default `C:/Python27` directory.

Now we need to add Python to the local PATH to access it from the command line. Either do this with the GUI or run `setx path "%path%;c:/Python27"` from the command prompt. To test if you've installed Python correctly, run `python --version` from the command line (it should say *Python 2.7.16*).

We also need to use Python's package manager PIP to install the `pycrypto` library (we use this for computing SHA256 hashes). First, upgrade pip by running `python -m pip install --upgrade pip`. Next, install (Microsoft Visual C++ Compiler for Python 2.7)[https://www.microsoft.com/en-us/download/details.aspx?id=44266], which PyCrypto uses for AES encryption/decryption. Lastly, install PyCrypto with `pip install --user pycrypto`.

### NPM and packages
NPM is a package manager used by EPSchedule to install `bower` and `grunt`. If you don't already have it installed, download it from https://www.npmjs.com/package/download. It should add itself to the local PATH by default.

Now we can install Bower and Grunt by running:
```
npm install bower -g
npm install grunt -g
```

The `-g` flag installs them globally, so we can use them from the command line. That's a good thing, because now we'll need to use them. First, we'll install all webcomponent dependencies by running
```
bower install
```

Then, we'll compress those dependencies into a single compressed file by running
```
grunt vulcanize
```

### Google App Engine

EPSchedule runs in the cloud on Google App Engine. To aid development, download Google's [Cloud SDK installer](https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe). Once it finishes installing, accept the **Start Cloud SDK Shell** and **Run gcloud init**. 

Google Cloud SDK will SDK will ask you to log into your Google account. It's not strictly necessary to do so, but it will make your life easier later. Follow the command line prompts to log in. However, when Cloud SDK asks if you would like to create a new project, **type `n` for no**.

### Testing your installation

To verify you've installed all prerequisites correctly, open a new command prompt and type `cd %HOMEPATH%/Documents/Github/EPSchedule` to navigate to the directory you installed EPSchedule into. Then, run `dev_appserver.py app.yaml` and navigate to http://localhost:8080/. If everything worked, you should see the login page for EPSchedule.

To run the EPSchedule unit tests, run `grunt runPythonTests` from the EPSchedule directory.

## Development

### Code style
We try to follow the Google [Python](https://google-styleguide.googlecode.com/svn/trunk/pyguide.html) and [JavaScript](https://google.github.io/styleguide/javascriptguide.xml) style guides.

### Contributing a patch
From your fork of the epschedule repo, submit a pull request. Be sure that all tests pass, and you have followed the code style guides mentioned above.
