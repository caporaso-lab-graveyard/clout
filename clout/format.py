#!/usr/bin/env python
from __future__ import division

__author__ = "Jai Ram Rideout"
__copyright__ = "Copyright 2012, The Clout Project"
__credits__ = ["Jai Ram Rideout"]
__license__ = "GPL"
__version__ = "0.9-dev"
__maintainer__ = "Jai Ram Rideout"
__email__ = "jai.rideout@gmail.com"
__status__ = "Development"

"""Module to format data structures for human consumption."""

def format_email_summary(test_suites_status):
    """Formats a string suitable for the body of an email message.

    Returns a string containing a summary of the testing results for each of
    the test suites. The summary will list the test suite name and whether it
    passed or not (which is dependent on the status of the return code of the
    test suite).

    Arguments:
        test_suites_status - a list of 2-element tuples, where the first
            element is the test suite label and the second element is the
            return value of the command that was run for the test suite. A
            non-zero return value indicates that something went wrong or the
            test suite didn't pass
    """
    summary = ''
    for test_suite_label, ret_val in test_suites_status:
        summary += test_suite_label + ': '
        summary += 'Pass\n' if ret_val == 0 else 'Fail\n'
    if summary != '':
        summary += '\n'
    return summary
