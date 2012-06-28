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
from os.path import basename
from smtplib import SMTP
from tempfile import TemporaryFile

from qiime.util import get_qiime_temp_dir, qiime_system_call

def run_test_suites(config_f, sc_config_fp, recipients_f, email_settings_f,
                    user, cluster_tag):
    # Parse the various configuration files first so that we know if there's
    # any outstanding problems with file formats before continuing.
    test_suites = _parse_config_file(config_f)
    recipients = _parse_email_list(recipients_f)
    email_settings = _parse_email_settings(email_settings_f)

    # Build up a list of commands to be executed (these include launching a
    # cluster, running the test suites, and terminating the cluster).
    commands = _build_test_execution_commands(test_suites, sc_config_fp, user,
                                              cluster_tag)

    # Create a unique temporary file to hold the results of the following
    # commands. This will automatically be deleted when it is closed or
    # garbage-collected, plus it isn't even visible in the file system on most
    # operating systems.
    log_f = TemporaryFile(prefix='automated_testing_log', suffix='.txt',
                          dir=get_qiime_temp_dir())

    # Execute the commands, keeping track of stdout and stderr in a temporary
    # file for each test suite. These will be used as attachments when the
    # email is sent. Since the temporary files will have a randomly-generated
    # name, we'll also specify what we want the file to be called when it is
    # attached to the email (we don't have to worry about having unique
    # filenames at that point).
    attachments = [(None, 'automated_testing_log.txt', log_f)]
    for command in commands:
        stdout, stderr, ret_val = qiime_system_call(command[1])
        log_f.write('Command:\n\n%s\n\n' % command[1])
        log_f.write('Stdout:\n\n%s\n' % stdout)
        log_f.write('Stderr:\n\n%s\n' % stderr)

        if command[0] is not None:
            # If the command is a test-suite-specific command, also log it in a
            # separate temporary file for the test suite.
            test_suite_f = TemporaryFile(prefix='automated_testing_log_%s' %
                    command[0], suffix='.txt', dir=get_qiime_temp_dir())
            test_suite_f.write('Command:\n\n%s\n\n' % command[1])
            test_suite_f.write('Stdout:\n\n%s\n' % stdout)
            test_suite_f.write('Stderr:\n\n%s\n' % stderr)
            attachments.append((command[0], '%s_results.txt' % command[0],
                                test_suite_f))

    # Set our file position to the beginning for all files since we are in
    # read/write mode and we need to read from the beginning again. Closing the
    # file will delete it.
    for attachment in attachments:
        attachment[2].seek(0, 0)
    summary = _build_email_summary(attachments)

    # Reposition again for additional reading.
    for attachment in attachments:
        attachment[2].seek(0, 0)
    _send_email(email_settings['smtp_server'], email_settings['smtp_port'],
                email_settings['sender'], email_settings['password'],
                recipients, summary, attachments)

def _parse_config_file(config_f):
    results = []
    used_test_suite_names = []
    for line in config_f:
        if not _can_ignore(line):
            fields = line.strip().split('\t')
            if len(fields) != 2:
                raise ValueError("Each line in the config file must contain "
                                 "exactly two fields separated by tabs.")
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
    # test suite run). We also need to keep track of whether the output of each
    # command should be put in its own test-suite-specific email attachment, or
    # whether it is a general logging command, such as the one below.
    commands = [(None, "starcluster -c %s start %s" %
                       (sc_config_fp, cluster_tag))]
    for test_suite in test_suites:
        test_suite_name, test_suite_exec = test_suite

        # To have the next command work without getting prompted to accept the
        # new host, the user must have 'StrictHostKeyChecking no' in their SSH
        # config (on the local machine). TODO: try to get starcluster devs to
        # add this feature to sshmaster.
        commands.append((test_suite_name,
                         "starcluster -c %s sshmaster -u %s %s '%s'" %
                         (sc_config_fp, user, cluster_tag, test_suite_exec)))

    # The second -c tells starcluster not to prompt us for termination
    # confirmation.
    commands.append((None, "starcluster -c %s terminate -c %s" %
                           (sc_config_fp, cluster_tag)))
    return commands

def _build_email_summary(attachments):
    summary = ''
    for test_suite_label, attachment_name, attachment_f in attachments:
        if test_suite_label is not None:
            summary += test_suite_label + ': '
            num_failures = _get_num_failures(attachment_f)
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
    msg['Subject'] = "Test suite results"
    msg['Date'] = formatdate(localtime=True)
 
    if attachments is not None:
        for test_suite_label, attachment_name, attachment_f in attachments:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment_f.read())
            encode_base64(part)
            part.add_header('Content-Disposition',
                            'attachment; filename="%s"' % attachment_name)
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
