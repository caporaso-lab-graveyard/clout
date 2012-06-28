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

"""Contains functions used in the run_test_suites.py script."""

from email.Encoders import encode_base64
from email.MIMEBase import MIMEBase
from email.MIMEMultipart import MIMEMultipart
from email.mime.text import MIMEText
from email.Utils import formatdate
from os import remove
from os.path import basename, dirname, isabs
from smtplib import SMTP
from tempfile import NamedTemporaryFile

from qiime.util import get_qiime_temp_dir

def run_test_suites(config_f, sc_config_fp, recipients_f, email_settings_f,
                    user, cluster_tag):
    # Parse the various configuration files.
    test_suites = _parse_config_file(config_f)
    recipients = _parse_email_list(recipients_f)
    email_settings = _parse_email_settings(email_settings_f)
    log_commands, test_suite_commands = _build_test_execution_commands(
            test_suites, sc_config_fp, user, cluster_tag)

    # Create a unique temporary file to hold the results of the following
    # commands.
    results_f = NamedTemporaryFile(mode='w', prefix='%s_test_suite_results'
            % test_suite_name, suffix='.txt', dir=get_qiime_temp_dir(),
            delete=True)

    summary = _build_email_summary(test_results_files, test_results_labels)
    _send_email(settings['smtp_server'], settings['smtp_port'],
                settings['sender'], settings['password'], recipients, summary,
                test_results_fps)

    log_f.close()
    remove(log_fp)

def _parse_config_file(config_f):
    results = []
    used_test_suite_names = []
    for line in config_f:
        if not _can_ignore(line):
            fields = line.strip().split('\t')
            if len(fields) != 3:
                raise ValueError("Each line in the config file must contain "
                                 "exactly three fields separated by tabs.")
            if fields[0] in used_test_suite_names:
                raise ValueError("The test suite label '%s' has already been "
                                 "used. Each test suite label must be unique."
                                 % fields[0])
            results.append(fields)
            used_test_suite_names.append(fields[0])
    if len(results) == 0:
        raise ValueError("The config file must contain at least one test "
                         "suite to run.")
    return results

def _parse_email_list(email_list_f):
    recipients = [line.strip() for line in email_list_f \
                  if not _can_ignore(line)]
    if len(recipients) == 0:
        raise ValueError("There are no email addresses to send the test suite "
                         "results to.")
    for address in recipients:
        if '@' not in address:
            raise ValueError("The email address '%s' doesn't look like a "
                             "valid email address." % address)
    return recipients

def _parse_email_settings(email_settings_f):
    required_fields = ['smtp_server', 'smtp_port', 'sender', 'password']
    settings = {}
    for line in email_settings_f:
        if not _can_ignore(line):
            try:
                setting, val = line.strip().split('\t')
            except:
                raise ValueError("The line '%s' in the email settings file "
                                 "must have exactly two fields separated by a "
                                 "tab." % line)
            if setting not in required_fields:
                raise ValueError("Unrecognized setting '%s' in email settings "
                                 "file. Valid settings are %r." % (setting,
                                 required_fields))
            settings[setting] = val
    if len(settings) != 4:
        raise ValueError("The email settings file does not contain one or "
                "more of the following required fields: %r" % required_fields)
    return settings

def _build_test_execution_commands(test_suites, sc_config_fp, user,
                                   cluster_tag):
    # Build up our list of commands to run (commands that are independent of a
    # test suite run).
    log_commands = ["starcluster -c %s start %s" % (sc_config_fp, cluster_tag)]

    # Run the test suite(s) remotely on a cluster using the provided
    # starcluster config file.
    test_suite_commands = {}
    for test_suite in test_suites:
        test_suite_name = test_suite[0]
        executable_fp = test_suite[1]
        setup_fp = test_suite[2]

        # Make sure we were given an absolute path.
        if not isabs(executable_fp):
            raise ValueError("The remote filepath '%s' must be an absolute "
                             "path." % executable_fp)
        # Find the directory containing the test suite executable.
        exec_dir = dirname(executable_fp)
        exec_name = basename(executable_fp)

        # To have the next command work without getting prompted to accept the
        # new host, the user must have 'StrictHostKeyChecking no' in their SSH
        # config (on the local machine). TODO: try to get starcluster devs to
        # add this feature to sshmaster.
        command = "starcluster -c %s sshmaster -u %s %s '" % (
                  sc_config_fp, user, cluster_tag)
        if setup_fp != 'NA':
            if not isabs(setup_fp):
                raise ValueError("The remote filepath '%s' must be an "
                                 "absolute path." % setup_fp)
            command += "source %s; " % setup_fp
        command += "cd %s; ./%s'" % (exec_dir, exec_name)
        test_suite_commands[test_suite_name] = command

    # The second -c tells starcluster not to prompt us for termination
    # confirmation.
    log_commands.append("starcluster -c %s terminate -c %s" %
                        (sc_config_fp, cluster_tag))
    return log_commands, test_suite_commands

def _build_email_summary(test_results_files, test_results_labels):
    if len(test_results_files) != len(test_results_labels):
        raise ValueError("You must provide the same number of test labels for "
                         "the number of test results files that are provided.")
    summary = ''
    for test_results_f, test_results_label in zip(test_results_files,
                                                  test_results_labels):
        summary += test_results_label + ': '
        num_failures = _get_num_failures(test_results_f)
        if num_failures == 0:
            summary += 'Pass\n'
        else:
            summary += 'Fail (%d failure' % num_failures
            if num_failures > 1:
                summary += 's'
            summary += ')\n'
    return summary

def _send_email(host, port, sender, password, recipients, body,
               attachments=None):
    """
    This code is largely based on the code found here:
    http://www.blog.pythonlibrary.org/2010/05/14/how-to-send-email-with-python/
    http://segfault.in/2010/12/sending-gmail-from-python/
    """
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = ', '.join(recipients)
    msg['Subject'] = "Test results"
    msg['Date'] = formatdate(localtime=True)
 
    if attachments is not None:
        for attachment in attachments:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(open(attachment, 'rb').read())
            encode_base64(part)
            part.add_header('Content-Disposition',
                    'attachment; filename="%s"' % basename(attachment))
            msg.attach(part)
    part = MIMEText('text', 'plain')
    part.set_payload(body)
    msg.attach(part)
 
    server = SMTP(host, port)
    server.ehlo()
    server.starttls()
    server.ehlo
    server.login(sender, password)
    server.sendmail(sender, recipients, msg.as_string())
    server.quit()

def _get_num_failures(test_results_f):
    failures = 0
    for line in test_results_f:
        line = line.strip()
        if line.startswith('FAILED ('):
            failures += int(line.split('=')[1][:-1])
    return failures

def _can_ignore(line):
    return False if line.strip() != '' and not line.strip().startswith('#') \
           else True
