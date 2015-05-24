#!/usr/bin/python

import os, sys

# Open a file
files = [f for f in os.listdir('.') if os.path.isfile(f)]
for f in files:
    if f[len(f) - 4:len(f)] == ".pdf":
        print f