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

from qiime.util import (parse_command_line_parameters, make_option)
from automated_testing.run_test_suites import run_test_suites

script_info = {}
script_info['brief_description'] = """Runs suite(s) of unit tests and emails results"""
script_info['script_description'] = """
This script runs one or more unit test suites remotely using StarCluster and
emails the results to a list of recipients. The email summarizes the results of
the test suites and includes the full output of running the test suite(s).

Please see config/conf.txt for sample configuration files to use as input to
this script.
"""
script_info['script_usage'] = []
script_info['script_usage'].append(("Execute unit test suites remotely",
"Executes the unit test suites defined in the input configuration file as the "
"'ubuntu' user and emails the test results to everyone in the provided email "
"list. The default starcluster template is used (as is defined in the input "
"starcluster config file and the starcluster cluster tag is 'nightly_tests'.",
"%prog -i conf.txt -s starcluster_config -u ubuntu -c nightly_tests "
"-l recipients.txt -e email_settings.txt"))
script_info['script_usage'].append(("Execute suites remotely using a custom "
"starcluster cluster template",
"Executes the test suites using a custom starcluster cluster template "
"'test-cluster' instead of the default cluster template in the starcluster "
"config file.",
"%prog -i conf.txt -s starcluster_config -u ubuntu -c nightly_tests "
"-l recipients.txt -e email_settings.txt -t test-cluster"))
script_info['output_description']= """
The script does not produce any output files.
"""

script_info['required_options'] = [
    make_option('-i','--input_config', type='existing_filepath',
        help='the input configuration file describing the test suites to be '
        'executed'),
    make_option('-s','--input_starcluster_config', type='existing_filepath',
        help='the input starcluster config file. The default cluster template '
        'will be used by the script to run the test suite(s) on unless the '
        '-t option is supplied. You should only need a single-node cluster'),
    make_option('-u','--user', type='string',
        help='the user to run the test suites as on the remote cluster'),
    make_option('-c','--cluster_tag', type='string',
        help='the starcluster cluster tag to use for the cluster that the '
        'test suite(s) will run on'),
    make_option('-l','--input_email_list', type='existing_filepath',
        help='the input email list file. This should be a file containing '
        'an email address on each line. Lines starting with "#" or lines that '
        'only contain whitespace or are blank will be ignored'),
    make_option('-e','--input_email_settings', type='existing_filepath',
        help='the input email settings file. This should be a file containing '
        'key/value pairs separated by a tab that tell the script how to send '
        'the email. "smtp_server", "smtp_port", "sender", and "password" must '
        'be defined')
]
script_info['optional_options'] = [
    make_option('-t','--cluster_template', type='string',
        help='the cluster template to use (defined in the starcluster config '
        'file) for running the test suite(s) on. You should only need a '
        'single-node cluster [default: starcluster config default template]',
        default=None)
]
script_info['version'] = __version__

def main():
    option_parser, opts, args = parse_command_line_parameters(**script_info)

    run_test_suites(open(opts.input_config, 'U'),
            opts.input_starcluster_config, open(opts.input_email_list, 'U'),
            open(opts.input_email_settings, 'U'), opts.user, opts.cluster_tag,
            opts.cluster_template)


if __name__ == "__main__":
    main()
