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

import signal
from email.Encoders import encode_base64
from email.MIMEBase import MIMEBase
from email.MIMEMultipart import MIMEMultipart
from email.mime.text import MIMEText
from email.Utils import formatdate
from smtplib import SMTP
from subprocess import PIPE, Popen
from tempfile import TemporaryFile

# This timing code is adapted from recipes provided at:
#   http://code.activestate.com/recipes/534115-function-timeout/
#   http://stackoverflow.com/questions/492519/timeout-on-a-python-function-call
class TimeExceededError(Exception):
    pass

def initiate_timeout(minutes):
    def timeout(signum, frame):
        raise TimeExceededError("Failed to run in allowed time (%d minutes)."
                                % minutes)

    signal.signal(signal.SIGALRM, timeout)
    # Set the 'alarm' to go off in minutes*60 seconds
    signal.alarm(minutes * 60)

def disable_timeout():
    # Turn off the alarm.
    signal.alarm(0)

def run_test_suites(config_f, sc_config_fp, recipients_f, email_settings_f,
                    user, cluster_tag, cluster_template=None,
                    setup_timeout=20, test_suites_timeout=240,
                    teardown_timeout=20, sc_exe_fp='starcluster'):
    """Runs the suite(s) of tests and emails the results to the recipients.

    This function does not return anything. This function is not unit-tested
    because there isn't a clean way to test it since it sends an email, starts
    up a cluster on Amazon EC2, etc. Nearly every other 'private' function that
    this function calls has been extensively unit-tested (whenever possible).
    Thus, the amount of untested code has been minimized and contained here.

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
        setup_timeout - the number of minutes to allow the cluster to be set up
            before aborting and attempting to terminate it
        test_suites_timeout - the number of minutes to allow *all* test suites
            to run before terminating the cluster
        teardown_timeout - the number of minutes to allow the cluster to be
            terminated before aborting
        sc_exe_fp - path to the starcluster executable
    """
    if setup_timeout < 1 or test_suites_timeout < 1 or teardown_timeout < 1:
        raise ValueError("The timeout (in minutes) cannot be less than 1.")

    # Parse the various configuration files first so that we know if there's
    # any outstanding problems with file formats before continuing.
    test_suites = _parse_config_file(config_f)
    recipients = _parse_email_list(recipients_f)
    email_settings = _parse_email_settings(email_settings_f)

    # Get the commands that need to be executed (these include launching a
    # cluster, running the test suites, and terminating the cluster).
    setup_cmds, test_suites_cmds, teardown_cmds = \
            _build_test_execution_commands(test_suites, sc_config_fp, user,
                                           cluster_tag, cluster_template,
                                           sc_exe_fp)

    # Execute the commands and build up the body of an email with the
    # summarized results as well as the output in log file attachments.
    email_body, attachments = _execute_commands_and_build_email(
            test_suites, setup_cmds, test_suites_cmds, teardown_cmds,
            setup_timeout, test_suites_timeout, teardown_timeout, cluster_tag)

    # Send the email.
    # TODO: this should be configurable by the user.
    subject = "Test suite results [automated testing system]"
    _send_email(email_settings['smtp_server'], email_settings['smtp_port'],
                email_settings['sender'], email_settings['password'],
                recipients, subject, email_body, attachments)

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
                                   cluster_tag, cluster_template=None,
                                   sc_exe_fp='starcluster'):
    """Builds up commands that need to be executed to run the test suites.

    These commands are starcluster commands to start/terminate a cluster,
    (setup/teardown commands, respectively) as well as execute commands over
    ssh to run the test suites (test suite commands).

    Returns a 3-element tuple containing the list of setup command strings,
    the list of test suite command strings, and the list of teardown command
    strings.

    Arguments:
        test_suites - the output of _parse_config_file()
        sc_config_fp - same as for run_test_suites()
        user - same as for run_test_suites()
        cluster_tag - same as for run_test_suites()
        cluster_template - same as for run_test_suites()
        sc_exe_fp - same as for run_test_suites()
    """
    setup_cmds, test_suite_cmds, teardown_cmds = [], [], []

    sc_start_cmd = "%s -c %s start " % (sc_exe_fp, sc_config_fp)
    if cluster_template is not None:
        sc_start_cmd += "-c %s " % cluster_template
    sc_start_cmd += "%s" % cluster_tag
    setup_cmds.append(sc_start_cmd)

    for test_suite_name, test_suite_exec in test_suites:
        # To have the next command work without getting prompted to accept the
        # new host, the user must have 'StrictHostKeyChecking no' in their SSH
        # config (on the local machine). TODO: try to get starcluster devs to
        # add this feature to sshmaster.
        test_suite_cmds.append("%s -c %s sshmaster -u %s %s '%s'" %
                (sc_exe_fp, sc_config_fp, user, cluster_tag, test_suite_exec))

    # The second -c tells starcluster not to prompt us for termination
    # confirmation.
    teardown_cmds.append("%s -c %s terminate -c %s" % (sc_exe_fp, sc_config_fp,
                                                       cluster_tag))
    return setup_cmds, test_suite_cmds, teardown_cmds

def _execute_commands_and_build_email(test_suites, setup_cmds,
                                      test_suites_cmds, teardown_cmds,
                                      setup_timeout, test_suites_timeout,
                                      teardown_timeout, cluster_tag):
    """Executes the test suite commands and builds the body of an email.

    Returns the body of an email containing the summarized results and any
    error message or issues that should be brought to the recipient's
    attention, and a list of attachments, which are the log files from running
    the commands.

    Arguments:
        test_suites - the output of _parse_config_file()
        setup_cmds - the output of _build_test_execution_commands()
        test_suites_cmds - the output of _build_test_execution_commands()
        teardown_cmds - the output of _build_test_execution_commands()
        setup_timeout - same as for run_test_suites()
        test_suites_timeout - same as for run_test_suites()
        teardown_timeout - same as for run_test_suites()
        cluster_tag - same as for run_test_suites()
    """
    email_body = ""
    attachments = []

    # Create a unique temporary file to hold the results of all commands.
    log_f = TemporaryFile(prefix='automated_testing_log', suffix='.txt')
    attachments.append(('automated_testing_log.txt', log_f))

    # Build up the body of the email as we execute the commands. First, execute
    # the setup commands.
    setup_cmds_succeeded = _execute_commands(setup_cmds, log_f, setup_timeout,
                                             stop_on_first_failure=True)[0]
    if setup_cmds_succeeded is None:
        email_body += "The maximum allowable cluster setup time of " + \
                      "%d " % setup_timeout
        email_body += "minutes was exceeded.\n\n"
    elif not setup_cmds_succeeded:
        email_body += "There were problems in starting the " + \
                "remote cluster while preparing to execute the " + \
                "test suite(s). Please check the attached log for " + \
                "more details.\n\n"
    else:
        # Execute each test suite command, keeping track of stdout and stderr
        # in a temporary file. These will be used as attachments when the
        # email is sent. Since the temporary files will have randomly-generated
        # names, we'll also specify what we want the file to be called when it
        # is attached to the email (we don't have to worry about having unique
        # filenames at that point).
        test_suites_cmds_succeeded, test_suites_cmds_status = \
                _execute_commands(test_suites_cmds, log_f, test_suites_timeout,
                                  log_individual_cmds=True)

        # It is okay if there are fewer test suites that got executed than
        # there were input test suites (which is possible if we encounter a
        # timeout). Just report the ones that finished.
        label_to_ret_val = []
        for (label, cmd), (test_suite_log_f, ret_val) in zip(test_suites,
                test_suites_cmds_status):
            label_to_ret_val.append((label, ret_val))
            attachments.append(('%s_results.txt' % label, test_suite_log_f))

        # Build a summary of the test suites that passed and those that didn't.
        email_body += _build_email_summary(label_to_ret_val)

        if test_suites_cmds_succeeded is None:
            untested_suites = [label for label, cmd in \
                               test_suites[len(test_suites_cmds_status):]]
            email_body += "The maximum allowable time of " + \
                          "%d " % test_suites_timeout
            email_body += "minutes for all test suites to run was " + \
                          "exceeded. The following test suites were not " + \
                          "tested: %s\n\n" % ', '.join(untested_suites)

    # Lastly, execute the teardown commands.
    cluster_termination_msg = "IMPORTANT: You should check that the " + \
            "cluster labelled with the tag '" + cluster_tag + "' was " + \
            "properly terminated. If not, you should manually terminate " + \
            "it.\n\n"
    teardown_cmds_succeeded = _execute_commands(teardown_cmds, log_f,
            teardown_timeout)[0]
    if teardown_cmds_succeeded is None:
        email_body += "The maximum allowable cluster termination time of " + \
                      "%d " % teardown_timeout
        email_body += "minutes was exceeded.\n\n%s" % cluster_termination_msg
    elif not teardown_cmds_succeeded:
        email_body += "There were problems in terminating the " + \
                "remote cluster. Please check the attached log for " + \
                "more details.\n\n%s" % cluster_termination_msg

    # Set our file position to the beginning for all attachments since we are
    # in read/write mode and we need to read from the beginning again. Closing
    # the file will delete it.
    for attachment in attachments:
        attachment[1].seek(0, 0)

    return email_body, attachments

def _execute_commands(cmds, log_f, timeout, stop_on_first_failure=False,
                      log_individual_cmds=False):
    """Executes commands and logs output to a file.

    Returns a 2-element tuple where the first element is a logical, where True
    indicates all commands succeeded, False indicates at least one command
    failed, and None indicates a timeout occurred. The second element of the
    tuple will be an empty list if log_individual_cmds is False, otherwise will
    be filled with 2-element tuples containing the individual TemporaryFile log
    files for each command, and the command's return code.

    Arguments:
        cmds - list of commands to run
        log_f - the file to write command output to
        timeout - the number of minutes to allow all of the commands to run
            collectively before aborting and returning the current results
        stop_on_first_failure - if True, will stop running all other commands
            once a command has a nonzero exit code
        log_individual_cmds - if True, will create a TemporaryFile for each
            command that is run and log the output separately (as well as to
            log_f). Will also keep track of the return values for each command
    """
    cmds_succeeded = True
    individual_cmds_status = []
    initiate_timeout(timeout)

    try:
        for cmd in cmds:
            stdout, stderr, ret_val = _system_call(cmd)
            cmd_str = 'Command:\n\n%s\n\n' % cmd
            stdout_str = 'Stdout:\n\n%s\n' % stdout
            stderr_str = 'Stderr:\n\n%s\n' % stderr
            log_f.write(cmd_str + stdout_str + stderr_str)

            if log_individual_cmds:
                individual_cmd_log_f = TemporaryFile(
                        prefix='automated_testing_log', suffix='.txt')
                individual_cmd_log_f.write(cmd_str + stdout_str + stderr_str)
                individual_cmds_status.append((individual_cmd_log_f, ret_val))

            if ret_val != 0:
                cmds_succeeded = False
                if stop_on_first_failure:
                    break
    except TimeExceededError:
        disable_timeout()
        cmds_succeeded = None
    return cmds_succeeded, individual_cmds_status

def _build_email_summary(test_suites_status):
    """Builds up a string suitable for the body of an email message.

    Returns a string containing a summary of the testing results for each of
    the test suites. The summary will list the test suite name and whether it
    passed or not (which is dependent on the status of the return code of the
    test suite).

    Arguments:
        test_suites_status - a list of 2-element tuples, where the first
        element is the test suite label and the second element is the return
        value of the command that was run for the test suite. A non-zero return
        value indicates that something went wrong or the test suite didn't pass
    """
    summary = ''
    for test_suite_label, ret_val in test_suites_status:
        summary += test_suite_label + ': '
        summary += 'Pass\n' if ret_val == 0 else 'Fail\n'
    if summary != '':
        summary += '\n'
    return summary

def _send_email(host, port, sender, password, recipients, subject, body,
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
        subject - the subject of the email
        body - the body of the email
        attachments - a list of 2-element tuples, where the first element is
            the filename that will be used for the email attachment (as the
            recipient will see it), and the second element is the file to be
            attached
    """
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = ', '.join(recipients)
    msg['Subject'] = subject
    msg['Date'] = formatdate(localtime=True)
 
    if attachments is not None:
        for attachment_name, attachment_f in attachments:
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

def _system_call(cmd):
    """Call cmd and return (stdout, stderr, return_value).
    
    This function is taken from QIIME's util module (originally named
    'qiime_system_call'.
    """
    proc = Popen(cmd, shell=True, universal_newlines=True, stdout=PIPE,
                 stderr=PIPE)
    # Communicate pulls all stdout/stderr from the PIPEs to avoid blocking--
    # don't remove this line!
    stdout, stderr = proc.communicate()
    return_value = proc.returncode
    return stdout, stderr, return_value
