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
from automated_testing.run_test_suites import run_test_suites

script_info = {}
script_info['brief_description'] = """Sends an email of test results"""
script_info['script_description'] = """
This script sends a email summarizing the results of one or more test suites.
The script accepts any number of test result files containing the output from
the python unittest module. The script will attempt to parse these and send an
email summarizing the results, as well as include the test result file as
attachments.
"""
script_info['script_usage'] = []
script_info['script_usage'].append(("Email test results to list of recipients",
"Emails the test results to everyone in the provided email list.",
"%prog -i test_results.txt -l recipients.txt -s email_settings.txt"))
script_info['script_usage'].append(("Email two test suite results with custom "
"labels", "Emails the test results of two different test suites to everyone "
"in the provided email list. The email will name the test suites using the "
"custom labels that are provided.",
"%prog -i qiime_test_results.txt,pycogent_test_results.txt -l recipients.txt "
"-s email_settings.txt -t QIIME,PyCogent"))
script_info['output_description']= """
The script does not produce any output files.
"""

script_info['required_options'] = [
    make_option('-i','--input_config',
        help='the input configuration file describing the test suites to be '
        'executed'),
    make_option('-s','--input_starcluster_config',
        help='the input starcluster config file. The default cluster template '
        'will be used by the script to run the test suite(s) on. You should '
        'only need a single-node cluster'),
    make_option('-u','--user',
        help='the user to run the test suites as on the remote cluster. Files '
        'will be written to the user\'s home on the remote cluster'),
    make_option('-c','--cluster_tag',
        help='the cluster tag to use for the cluster that the test suite(s) '
        'will run on'),
    make_option('-l','--input_email_list',
        help='the input email list file. This should be a file containing '
        'an email address on each line. Lines starting with "#" or lines that '
        'only contain whitespace or are blank will be ignored'),
    make_option('-e','--input_email_settings',
        help='the input email settings file. This should be a file containing '
        'key/value pairs separated by a tab that tell the script how to send '
        'the email. smtp_server, smtp_port, sender, and password must be '
        'defined')
]
script_info['optional_options'] = []
script_info['version'] = __version__

def main():
    option_parser, opts, args = parse_command_line_parameters(**script_info)

    run_test_suites(open(opts.input_config, 'U'),
            opts.input_starcluster_config, open(opts.input_email_list, 'U'),
            open(opts.input_email_settings, 'U'), opts.user, opts.cluster_tag)


if __name__ == "__main__":
    main()
