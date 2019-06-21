#!/usr/bin/python

import optparse
import os
import tarfile
import sys
import unittest
import urllib
import urllib2
import zipfile

TEST_MODULES_DIR = 'test_modules/'
GAE_UPDATECHECK_URL = 'https://appengine.google.com/api/updatecheck'
GAE_SDK_URL = 'https://storage.googleapis.com/appengine-sdks/featured/'
WEBTEST_URL = 'https://nodeload.github.com/Pylons/webtest/tar.gz/master'
WEBTEST_FILE = 'webtest-master.tar.gz'
BS4_URL = 'https://pypi.python.org/packages/source/b/beautifulsoup4/'
BS4_FILE = 'beautifulsoup4-4.4.0.tar.gz'

def make_path(filename):
    return TEST_MODULES_DIR + filename

def download(url, filename):
    print 'Downloading ' + filename
    urllib.urlretrieve(url, make_path(filename))

def explode_zip(zip_filename, out_path):
    print 'Exploding ' + zip_filename
    f = zipfile.ZipFile(make_path(zip_filename), 'r')
    f.extractall(out_path)

def explode_tgz(tgz_filename, out_path):
    print 'Exploding ' + tgz_filename
    f = tarfile.open(make_path(tgz_filename), 'r:gz')
    f.extractall(out_path)

def setup_tests():
    if not os.path.isdir(TEST_MODULES_DIR):
        os.mkdir(TEST_MODULES_DIR)

    # Install GAE SDK
    response = urllib2.urlopen(GAE_UPDATECHECK_URL)
    params = response.read().split('\n')
    for param in params:
        keyval = param.split(': ')
        if keyval[0] == 'release':
            gae_sdk_version = keyval[1].replace('"', '')
            break

    gae_sdk_zip_file = 'google_appengine_' + gae_sdk_version + '.zip'
    gae_sdk_path = make_path(gae_sdk_zip_file[:-4])
    if not os.path.isdir(gae_sdk_path):
        download(GAE_SDK_URL + gae_sdk_zip_file, gae_sdk_zip_file)
        explode_zip(gae_sdk_zip_file, gae_sdk_path)

    # Install webtest
    webtest_path = TEST_MODULES_DIR + 'webtest-master'
    if not os.path.isdir(webtest_path):
        download(WEBTEST_URL, WEBTEST_FILE)
        explode_tgz(WEBTEST_FILE, TEST_MODULES_DIR)

    # Install BeautifulSoup
    bs4_path = TEST_MODULES_DIR + BS4_FILE[:-7]
    if not os.path.isdir(bs4_path):
        download(BS4_URL + BS4_FILE, BS4_FILE)
        explode_tgz(BS4_FILE, TEST_MODULES_DIR)

    # TODO(juberti): clean this up to not have these nested dirs
    sys.path.insert(0, gae_sdk_path + '/google_appengine')
    print gae_sdk_path + '/google_appengine'
    import dev_appserver
    dev_appserver.fix_sys_path()
    sys.path.append(webtest_path)
    sys.path.append(bs4_path)

def run_tests(test_path):
    suite = unittest.loader.TestLoader().discover(test_path,
                                                  pattern="*test.py")
    return unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()

USAGE = """%prog TEST_PATH
Run unit tests for App Engine apps.

TEST_PATH    Path to package containing test modules."""

if __name__ == '__main__':
    parser = optparse.OptionParser(USAGE)
    options, args = parser.parse_args()
    if len(args) != 1:
        print 'Error: Exactly 1 argument required.'
        parser.print_help()
        sys.exit(1)
    TEST_PATH = args[0]
    setup_tests()
    sys.exit(not run_tests(TEST_PATH))
