#!/usr/bin/env python
from __future__ import division

__author__ = "Jai Rideout"
__copyright__ = "Copyright 2012, The QIIME project"
__credits__ = ["Jai Ram Rideout"]
__license__ = "GPL"
__version__ = "1.5.0-dev"
__maintainer__ = "Jai Ram Rideout"
__email__ = "jai.rideout@gmail.com"
__status__ = "Development"

from qiime.util import (parse_command_line_parameters,
                        get_options_lookup,
                        make_option)

from automated_testing.email_test_results import (get_num_failures,
                                                  parse_email_list)

script_info = {}
script_info['brief_description'] = """Sends an email of test results"""
script_info['script_description'] = ""
script_info['script_usage'] = []
script_info['script_usage'].append(("Email test results to list of recipients",
"Emails the test results to everyone in the provided email list.",
"%prog -i test_results.txt -l recipients.txt"))
script_info['output_description']= """
The script does not produce any output files.
"""

script_info['required_options'] = [
    make_option('-i','--input_test_results',
        help='the input test results file(s). Multiple filepaths should be '
        'comma-separated. Each file should contain the output of running a '
        'suite of python unit tests'),
    make_option('-l','--input_email_list',
        help='the input email list file. This should be a file containing '
        'an email address on each line. Lines starting with "#" or lines that '
        'only contain whitespace or are blank will be ignored')
]
script_info['optional_options'] = []
script_info['version'] = __version__

def main():
    option_parser, opts, args = parse_command_line_parameters(**script_info)

    recipients = parse_email_list(open(opts.input_email_list, 'U'))

    # Parse the test results to pull out a summary.
    summary = ""
    test_results_fps = opts.input_test_results.split(',')
    for test_results_fp in test_results_fps:
        summary += test_results_fp + ': '
        num_failures = get_num_failures(open(test_results_fp, 'U'))
        if num_failures == 0:
            summary += 'Pass\n'
        else:
            summary += 'Fail (%d failure' % num_failures
            if num_failures > 1:
                summary += 's'
            summary += ')\n'

    print "Send email to: "
    print recipients
    print "Message: "
    print summary

if __name__ == "__main__":
    main()
