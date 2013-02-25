#!/usr/bin/env python
from __future__ import division

__author__ = "Jai Ram Rideout"
__copyright__ = "Copyright 2012-2013, The Clout Project"
__credits__ = ["Jai Ram Rideout"]
__license__ = "GPLv2"
__version__ = "0.9-dev"
__maintainer__ = "Jai Ram Rideout"
__email__ = "jai.rideout@gmail.com"

"""Module to run test suites and publish the results."""

from tempfile import TemporaryFile

from clout.format import format_email_summary
from clout.parse import (parse_config_file, parse_email_list,
                         parse_email_settings)
from clout.static import MAX_SPOT_BID
from clout.util import CommandExecutor, send_email

def run_test_suites(config_f,
                    sc_config_fp,
                    recipients_f,
                    email_settings_f,
                    cluster_tag,
                    cluster_template=None,
                    user='root',
                    spot_bid=None,
                    setup_timeout=20.0,
                    test_suites_timeout=240.0,
                    teardown_timeout=20.0,
                    sc_exe_fp='starcluster',
                    suppress_spot_bid_check=False):
    """Runs the test suites and emails the results to the recipients.

    This function does not return anything. This function is not unit-tested
    because there isn't a clean way to test it since it sends an email, starts
    up a cluster on Amazon EC2, etc. Nearly every other 'private' function that
    this function calls has been extensively unit-tested (whenever possible).
    Thus, the amount of untested code has been minimized and contained here.

    Arguments:
        config_f - the input configuration file describing the test suites to
            be run
        sc_config_fp - the starcluster config filepath that will be used to
            start/terminate the cluster that the tests will be run on
        recipients_f - the file containing email addresses of those who should
            receive the test suite results
        email_settings_f - the file containing email (SMTP) settings to allow
            the script to send an email
        cluster_tag - the starcluster cluster tag to use when creating the
            cluster (a string)
        cluster_template - the starcluster cluster template to use in the
            starcluster config file. If not provided, the default cluster
            template in the starcluster config file will be used
        user - the user who the tests should be run as on the cluster
            (a string)
        spot_bid - the maximum bid in USD to use for spot instances (a float).
            If None, "on-demand" flat rates will be used for all instances
        setup_timeout - the number of minutes to allow the cluster to be set up
            before aborting and attempting to terminate it. Must be a float, to
            allow for fractions of a minute
        test_suites_timeout - the number of minutes to allow *all* test suites
            to run before terminating the cluster. Must be a float, to allow
            for fractions of a minute
        teardown_timeout - the number of minutes to allow the cluster to be
            terminated before aborting. Must be a float, to allow for fractions
            of a minute
        sc_exe_fp - path to the starcluster executable
        suppress_spot_bid_check - if True, suppress sanity checking of
            spot_bid. By default, if spot_bid is greater than
            clout.static.MAX_SPOT_BID, an error will be raised
    """
    if setup_timeout <= 0 or test_suites_timeout <= 0 or teardown_timeout <= 0:
        raise ValueError("The timeout (in minutes) must be greater than zero.")

    if spot_bid is not None:
        try:
            spot_bid = float(spot_bid)
        except ValueError:
            raise ValueError("Could not convert max spot bid to a float. Max "
                             "spot bid must be numeric.")

        if spot_bid <= 0:
            raise ValueError("Max spot bid of $%.2f must be greater than zero."
                             % spot_bid)

        if not suppress_spot_bid_check and spot_bid > MAX_SPOT_BID:
            raise ValueError("Max spot bid of $%.2f seems very high. If you "
                             "are sure this is the max spot bid that you want "
                             "to use, you can suppress this check with "
                             "--supprress_spot_bid_check." % spot_bid)

    # Parse the various configuration files first so that we know if there's
    # any outstanding problems with file formats before continuing.
    test_suites = parse_config_file(config_f)
    recipients = parse_email_list(recipients_f)
    email_settings = parse_email_settings(email_settings_f)

    # Get the commands that need to be executed (these include launching a
    # cluster, running the test suites, and terminating the cluster).
    setup_cmds, test_suites_cmds, teardown_cmds = \
            _build_test_execution_commands(test_suites, sc_config_fp,
                                           cluster_tag, cluster_template, user,
                                           spot_bid, sc_exe_fp)

    # Execute the commands and build up the body of an email with the
    # summarized results as well as the output in log file attachments.
    email_body, attachments = _execute_commands_and_build_email(
            test_suites, setup_cmds, test_suites_cmds, teardown_cmds,
            setup_timeout, test_suites_timeout, teardown_timeout, cluster_tag)

    # Send the email.
    # TODO: this should be configurable by the user.
    subject = "Test suite results [Clout testing system]"
    send_email(email_settings['smtp_server'], email_settings['smtp_port'],
                email_settings['sender'], email_settings['password'],
                recipients, subject, email_body, attachments)

def _build_test_execution_commands(test_suites, sc_config_fp, cluster_tag,
                                   cluster_template=None, user='root',
                                   spot_bid=None, sc_exe_fp='starcluster'):
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
        spot_bid - same as for run_test_suites()
        cluster_tag - same as for run_test_suites()
        cluster_template - same as for run_test_suites()
        sc_exe_fp - same as for run_test_suites()
    """
    setup_cmds, test_suite_cmds, teardown_cmds = [], [], []

    sc_start_cmd = '%s -c %s start ' % (sc_exe_fp, sc_config_fp)

    if cluster_template is not None:
        sc_start_cmd += '-c %s ' % cluster_template

    if spot_bid is not None:
        sc_start_cmd += '-b %.2f --force-spot-master ' % spot_bid

    sc_start_cmd += cluster_tag
    setup_cmds.append(sc_start_cmd)

    for test_suite_name, test_suite_exec in test_suites:
        # To have the next command work without getting prompted to accept the
        # new host, the user must have 'StrictHostKeyChecking no' in their SSH
        # config (on the local machine). TODO: try to get starcluster devs to
        # add this feature to sshmaster.
        test_suite_cmds.append('%s -c %s sshmaster -u %s %s \'%s\'' %
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
    log_f = TemporaryFile(prefix='clout_log', suffix='.txt')
    attachments.append(('complete_log.txt', log_f))

    # Build up the body of the email as we execute the commands. First, execute
    # the setup commands.
    cmd_executor = CommandExecutor(setup_cmds, log_f,
                                   stop_on_first_failure=True)
    setup_cmds_succeeded = cmd_executor(setup_timeout)[0]

    if setup_cmds_succeeded is None:
        email_body += ("The maximum allowable cluster setup time of %s "
                       "minute(s) was exceeded.\n\n" % str(setup_timeout))
    elif not setup_cmds_succeeded:
        email_body += ("There were problems in starting the cluster while "
                       "preparing to execute the test suite(s). Please check "
                       "the attached log for more details.\n\n")
    else:
        # Execute each test suite command, keeping track of stdout and stderr
        # in a temporary file. These will be used as attachments when the
        # email is sent. Since the temporary files will have randomly-generated
        # names, we'll also specify what we want the file to be called when it
        # is attached to the email (we don't have to worry about having unique
        # filenames at that point).
        cmd_executor.cmds = test_suites_cmds
        cmd_executor.stop_on_first_failure = False
        cmd_executor.log_individual_cmds = True
        test_suites_cmds_succeeded, test_suites_cmds_status = \
                cmd_executor(test_suites_timeout)

        # It is okay if there are fewer test suites that got executed than
        # there were input test suites (which is possible if we encounter a
        # timeout). Just report the ones that finished.
        label_to_ret_val = []
        for (label, cmd), (test_suite_log_f, ret_val) in \
                zip(test_suites, test_suites_cmds_status):
            label_to_ret_val.append((label, ret_val))
            attachments.append(('%s_results.txt' % label, test_suite_log_f))

        # Build a summary of the test suites that passed and those that didn't.
        email_body += format_email_summary(label_to_ret_val)

        if test_suites_cmds_succeeded is None:
            timeout_test_suite = \
                    test_suites[len(test_suites_cmds_status) - 1][0]
            untested_suites = [label for label, cmd in
                               test_suites[len(test_suites_cmds_status):]]
            email_body += ("The maximum allowable time of %s minute(s) for "
                           "all test suites to run was exceeded. The timeout "
                           "occurred while running the %s test suite." %
                           (str(test_suites_timeout), timeout_test_suite))
            if untested_suites:
                email_body += (" The following test suites were not tested: "
                               "%s\n\n" % ', '.join(untested_suites))

    # Lastly, execute the teardown commands.
    cluster_termination_msg = ("IMPORTANT: You should check that the cluster "
                               "labelled with the tag '%s' was properly "
                               "terminated. If not, you should manually "
                               "terminate it.\n\n" % cluster_tag)

    cmd_executor.cmds = teardown_cmds
    cmd_executor.stop_on_first_failure = False
    cmd_executor.log_individual_cmds = False
    teardown_cmds_succeeded = cmd_executor(teardown_timeout)[0]

    if teardown_cmds_succeeded is None:
        email_body += ("The maximum allowable cluster termination time of "
                       "%s minute(s) was exceeded.\n\n%s" %
                       (str(teardown_timeout), cluster_termination_msg))
    elif not teardown_cmds_succeeded:
        email_body += ("There were problems in terminating the cluster. "
                       "Please check the attached log for more details.\n\n%s"
                       % cluster_termination_msg)

    # Set our file position to the beginning for all attachments since we are
    # in read/write mode and we need to read from the beginning again. Closing
    # the file will delete it.
    for attachment in attachments:
        attachment[1].seek(0, 0)

    return email_body, attachments
