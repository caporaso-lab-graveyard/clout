#!/usr/bin/env python
from __future__ import division

__author__ = "Jai Ram Rideout"
__copyright__ = "Copyright 2012, The QIIME project"
__credits__ = ["Jai Ram Rideout"]
__license__ = "GPL"
__version__ = "1.5.0-dev"
__maintainer__ = "Jai Ram Rideout"
__email__ = "jai.rideout@gmail.com"
__status__ = "Development"

"""Contains functions used in the email_test_results.py script."""

def parse_email_list(email_list_lines):
    return [line.strip() for line in email_list_lines if not _can_ignore(line)]

def parse_email_settings(email_settings_lines):
    settings = {}
    for line in email_settings_lines:
        if not _can_ignore(line):
            setting, val = line.strip().split(' ')
            settings[setting] = val
    return settings

def get_num_failures(test_results_lines):
    failures = 0
    # Get the last line in the file.
    for status_line in test_results_lines:
        status_line = status_line.strip()
    if status_line != 'OK':
        failures = int(status_line.split('=')[1][:-1])
    return failures

def _can_ignore(line):
    return False if line.strip() != '' and not line.strip().startswith('#') \
           else True
