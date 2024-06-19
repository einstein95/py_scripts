#!/usr/bin/python3
from datetime import datetime
from os import utime
from os.path import getmtime
from sys import argv
from time import mktime

infile1 = argv[1]
infile2 = argv[2]
date = datetime.fromtimestamp(getmtime(infile1))
modTime = mktime(date.timetuple())
utime(infile2, (modTime, modTime))
