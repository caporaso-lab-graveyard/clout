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
from smtplib import SMTP
from tempfile import TemporaryFile

from qiime.util import get_qiime_temp_dir, qiime_system_call

def run_test_suites(config_f, sc_config_fp, recipients_f, email_settings_f,
                    user, cluster_tag, cluster_template=None):
    """Runs the suite(s) of tests and emails the results to the recipients.

    This function does not return anything. This function is not unit-tested
    because there isn't a clean way to test it since it sends an email, starts
    up a cluster on Amazon EC2, etc. Every other private function that this
    function calls has been extensively unit-tested (whenever possible). Thus,
    the amount of untested code has been minimized and contained here.

    Arguments:
        config_f - the input configuration file describing the test suites to
            be run
        sc_config_fp - the starcluster config filepath that will be used to
            start/terminate the remote cluster that the tests will be run on
        recipients_f - the file containing email addresses of those who should
            receive the test suite results
        email_settings_f - the file containing email (SMTP) settings to allow
            the script to send an email
        user - the user who the tests should be run as on the remote cluster (a
            string)
        cluster_tag - the starcluster cluster tag to use when creating the
            remote cluster (a string)
        cluster_template - the starcluster cluster template to use in the
            starcluster config file. If not provided, the default cluster
            template in the starcluster config file will be used
    """
    # Parse the various configuration files first so that we know if there's
    # any outstanding problems with file formats before continuing.
    test_suites = _parse_config_file(config_f)
    recipients = _parse_email_list(recipients_f)
    email_settings = _parse_email_settings(email_settings_f)

    # Build up a list of commands to be executed (these include launching a
    # cluster, running the test suites, and terminating the cluster).
    commands = _build_test_execution_commands(test_suites, sc_config_fp, user,
                                              cluster_tag, cluster_template)

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
    commands_status = []
    for command in commands:
        stdout, stderr, ret_val = qiime_system_call(command[1])
        commands_status.append((command[0], ret_val))
        log_f.write('Command:\n\n%s\n\n' % command[1])
        log_f.write('Stdout:\n\n%s\n' % stdout)
        log_f.write('Stderr:\n\n%s\n' % stderr)

        # If the command is a test-suite-specific command, also log it in a
        # separate temporary file for the test suite.
        if command[0] is not None:
            test_suite_f = TemporaryFile(prefix='automated_testing_log_%s' %
                    command[0], suffix='.txt', dir=get_qiime_temp_dir())
            test_suite_f.write('Command:\n\n%s\n\n' % command[1])
            test_suite_f.write('Stdout:\n\n%s\n' % stdout)
            test_suite_f.write('Stderr:\n\n%s\n' % stderr)
            attachments.append((command[0], '%s_results.txt' % command[0],
                                test_suite_f))

    # Build a summary of the test suites that passed and those that didn't.
    # This will go in the body of the email.
    summary = _build_email_summary(commands_status)

    # Set our file position to the beginning for all files since we are in
    # read/write mode and we need to read from the beginning again. Closing the
    # file will delete it.
    for attachment in attachments:
        attachment[2].seek(0, 0)
    _send_email(email_settings['smtp_server'], email_settings['smtp_port'],
                email_settings['sender'], email_settings['password'],
                recipients, summary, attachments)

def _parse_config_file(config_f):
    """Parses and validates a configuration file describing test suites.

    Returns a list of lists containing the test suite label as the first
    element and the command string needed to execute the test suite as the
    second element.

    Arguments:
        config_f - the input configuration file describing test suites
    """
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
    """Parses and validates a file containing email addresses.
    
    Returns a list of email addresses.

    Arguments:
        email_list_f - the input file containing email addresses
    """
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
    """Parses and validates a file containing email SMTP settings.

    Returns a dictionary with the key/value pairs 'smtp_server', 'smtp_port',
    'sender', and 'password' defined.

    Arguments:
        email_settings_f - the input file containing tab-separated email
            settings
    """
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
                                   cluster_tag, cluster_template=None):
    """Builds up commands that need to be executed to run the test suites.

    These commands are generally starcluster commands to start/terminate a
    cluster, as well as execute commands over ssh to run the test suites.

    Returns a list of 2-element tuples, where the first element is the test
    suite label that the command belongs to (or None if the command is a
    non test-suite-specific command, such as for starting or terminating the
    cluster). The second element in the tuple will be the command string
    itself.
    
    Arguments:
        test_suites - the output of _parse_config_file()
        sc_config_fp - the starcluster config filepath (a string)
        user - the user to run the tests as remotely (a string)
        cluster_tag - the cluster tag to use for the remote cluster that will
            be created (a string)
        cluster_template - the starcluster cluster template to use to create
            the new remote cluster (a string). If not provided, the starcluster
            default cluster template will be used (as defined in the
            starcluster config file)
    """
    # Build up our list of commands to run (commands that are independent of a
    # test suite run). We also need to keep track of whether the output of each
    # command should be put in its own test-suite-specific email attachment, or
    # whether it is a general logging command, such as the one below.
    commands = []
    starcluster_start_command = "starcluster -c %s start " % sc_config_fp
    if cluster_template is not None:
        starcluster_start_command += "-c %s " % cluster_template
    starcluster_start_command += "%s" % cluster_tag
    commands.append((None, starcluster_start_command))

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

def _build_email_summary(commands_status):
    """Builds up a string suitable for the body of an email message.

    Returns a string containing a summary of the testing results for each of
    the test suites. The summary will list the test suite name and whether it
    passed or not (which is dependent on the status of the return code of the
    test suite). The summary will also indicate if there were any other
    problems in setting up the environment to run the test suite(s).

    Arguments:
        commands_status - a list of 2-element tuples, where the first
        element is the test suite name/label (or None if the command is not
        associated with a particular test suite, but rather in the
        setup/teardown of the environment to allow for the test suites to run).
        The second element is the return value of the command that was run. A
        non-zero return value indicates that something went wrong or the test
        suite didn't pass
    """
    summary = ''
    encountered_log_failure = False
    for test_suite_label, ret_val in commands_status:
        if test_suite_label is not None:
            # We have the return value of a test suite command.
            summary += test_suite_label + ': '
            summary += 'Pass\n' if ret_val == 0 else 'Fail\n'
        else:
            # We have the return value of a setup/teardown command.
            if ret_val != 0 and not encountered_log_failure:
                encountered_log_failure = True
                summary += "There were problems in setting up or tearing " + \
                           "down the remote cluster while preparing to " + \
                           "execute the test suite(s). Please check the " + \
                           "attached log for more details.\n\n"
    return summary

def _send_email(host, port, sender, password, recipients, body,
               attachments=None):
    """Sends an email (optionally with attachments).

    This function does not return anything. It is not unit tested because it
    sends an actual email.

    This code is largely based on the code found here:
    http://www.blog.pythonlibrary.org/2010/05/14/how-to-send-email-with-python/
    http://segfault.in/2010/12/sending-gmail-from-python/

    Arguments:
        host - the STMP server to send the email with
        port - the port number of the SMTP server to connect to
        sender - the sender email address (i.e. who this message is from). This
            will be used as the username when logging into the SMTP server
        password - the password to log into the SMTP server with
        recipients - a list of email addresses to send the email to
        body - a string that will be the body of the email message
        attachments - a list of 3-element tuples, where the first element is
            the test suite name/label that the email attachment is related to
            (or None if the attachment is an overall log file for all of the
            commands that were run). The second element is a string containing
            the filename that will be used for the email attachment (as the
            recipient will see it), and the third element is a file containing
            the stdout/stderr of the test suite (or all test suites if it is
            the log file attachment).  This last element is the actual content
            of the attachment. If this parameter is not provided, no
            attachments will be included with the message.
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

def _can_ignore(line):
    """Returns True if the line can be ignored (comment or blank line)."""
    return False if line.strip() != '' and not line.strip().startswith('#') \
           else True
