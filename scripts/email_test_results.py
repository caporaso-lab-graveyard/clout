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

from email import Encoders
from email.MIMEBase import MIMEBase

from os.path import basename
from qiime.util import (parse_command_line_parameters,
                        get_options_lookup,
                        make_option)

from automated_testing.email_test_results import (build_email_summary,
        parse_email_list, parse_email_settings, send_email)

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
        'only contain whitespace or are blank will be ignored'),
    make_option('-s','--input_email_settings',
        help='the input email settings file. This should be a file containing '
        'key/value pairs separated by a space that tell the script how to '
        'send the email. smtp_server, smtp_port, sender, and password must be '
        'defined')
]
script_info['optional_options'] = [
    make_option('-t', '--test_labels', type='string',
        help='comma-separated list of labels for each input test results '
             'file, where the list of labels should be in quotes (e.g. '
             '"QIIME,PyCogent,PyNAST"). If supplied, this list must be the '
             'same length as the list of input test results files. If not '
             'provided, the filepaths of the input test results files will '
             'be used to label each test\'s results [default: %default]',
             default=None)]
script_info['version'] = __version__

def main():
    option_parser, opts, args = parse_command_line_parameters(**script_info)

    recipients = parse_email_list(open(opts.input_email_list, 'U'))
    settings = parse_email_settings(open(opts.input_email_settings, 'U'))
    test_results_fps = opts.input_test_results.split(',')

    if opts.test_labels is not None:
        test_results_labels = opts.test_labels.split(',')
    else:
        test_results_labels = test_results_fps

    summary = build_email_summary(
        [open(test_results_fp, 'U') for test_results_fp in test_results_fps],
        test_results_labels)

    send_email(settings['smtp_server'], settings['smtp_port'],
               settings['sender'], settings['password'], recipients, summary)


if __name__ == "__main__":
    main()
