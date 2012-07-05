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

from optparse import make_option, OptionParser, OptionGroup

from automated_testing.run_test_suites import run_test_suites

script_usage = "Detailed usage examples can be found in the README.md file."
script_description = """This script runs one or more unit test suites remotely
using StarCluster/Amazon EC2 and emails the results to a list of recipients.
The email summarizes the results of the test suites and includes the full
output of running the test suites.

Please see the README file for more detailed descriptions of the configuration
files that are required by this script. Examples are included under the config
directory.
"""

parser = OptionParser(usage=script_usage, description=script_description,
                      version=__version__)
parser.set_defaults(verbose=True)

required_group = OptionGroup(parser, 'Required Options')
required_options = [
    make_option('-i', '--input_config', type='string',
        help='the input configuration file describing the test suites to be '
        'executed. This is a tab-separated file with two fields. The first '
        'field is the label/name of the test suite and the second field is '
        'the command(s) to run on the remote cluster to execute the test '
        'suite'),
    make_option('-s', '--input_starcluster_config', type='string',
        help='the input starcluster config file. The default cluster template '
        'will be used by the script to run the test suite(s) on unless the '
        '-t option is supplied. You should only need a single-node cluster'),
    make_option('-u', '--user', type='string',
        help='the user to run the test suites as on the remote cluster'),
    make_option('-c', '--cluster_tag', type='string',
        help='the starcluster cluster tag to use for the cluster that the '
        'test suites will run on'),
    make_option('-l', '--input_email_list', type='string',
        help='the input email list file. This should be a file containing '
        'an email address on each line. Lines starting with "#" or lines that '
        'only contain whitespace or are blank will be ignored'),
    make_option('-e', '--input_email_settings', type='string',
        help='the input email settings file. This should be a file containing '
        'key/value pairs separated by a tab that tell the script how to send '
        'the email. "smtp_server", "smtp_port", "sender", and "password" must '
        'be defined')
]

required_group.add_options(required_options)
parser.add_option_group(required_group)

optional_group = OptionGroup(parser, 'Optional Options')
optional_options = [
    make_option('-t', '--cluster_template', type='string',
        help='the cluster template to use (defined in the starcluster config '
        'file) for running the test suite(s) on. You should only need a '
        'single-node cluster [default: starcluster config default template]',
        default=None)
]

optional_group.add_options(optional_options)
parser.add_option_group(optional_group)

def main():
    opts, args = parser.parse_args()

    if opts.input_config is None:
        parser.print_help()
        parser.error('You must specify an input test suite configuration '
                     'file.')
    if opts.input_starcluster_config is None:
        parser.print_help()
        parser.error('You must specify an input StarCluster configuration '
                     'file.')
    if opts.user is None:
        parser.print_help()
        parser.error('You must specify a user to run the test suites as.')
    if opts.cluster_tag is None:
        parser.print_help()
        parser.error('You must specify a cluster tag.')
    if opts.input_email_list is None:
        parser.print_help()
        parser.error('You must specify an input list of email addresses.')
    if opts.input_email_settings is None:
        parser.print_help()
        parser.error('You must specify an input email settings file.')

    run_test_suites(open(opts.input_config, 'U'),
            opts.input_starcluster_config, open(opts.input_email_list, 'U'),
            open(opts.input_email_settings, 'U'), opts.user, opts.cluster_tag,
            opts.cluster_template)


if __name__ == "__main__":
    main()
