#!/usr/bin/python3
from datetime import datetime
from os import utime
from os.path import getmtime
from sys import argv
from time import mktime

source_file = argv[1]
target_file = argv[2]
source_file_date = datetime.fromtimestamp(getmtime(source_file))
source_file_mod_time = mktime(source_file_date.timetuple())
utime(target_file, (source_file_mod_time, source_file_mod_time))
