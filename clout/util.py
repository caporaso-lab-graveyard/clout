#!/usr/bin/env python
from __future__ import division

__author__ = "Jai Ram Rideout"
__copyright__ = "Copyright 2012-2013, The Clout Project"
__credits__ = ["Jai Ram Rideout"]
__license__ = "GPLv2"
__version__ = "0.9-dev"
__maintainer__ = "Jai Ram Rideout"
__email__ = "jai.rideout@gmail.com"

"""Module to provide miscellaneous utility functionality."""

from email.Encoders import encode_base64
from email.MIMEBase import MIMEBase
from email.MIMEMultipart import MIMEMultipart
from email.mime.text import MIMEText
from email.Utils import formatdate
from os import killpg, setsid
from signal import SIGTERM
from smtplib import SMTP
from subprocess import PIPE, Popen
from tempfile import TemporaryFile
from threading import Lock, Thread

class CommandExecutor(object):
    """Class to run commands in a separate thread.

    Provides support for timeouts (e.g. useful for commands that may hang
    indefinitely) and for capturing stdout, stderr, and return value of each
    command. Output is logged to a file (or optionally to separate files for
    each command).

    This class is the single place in Clout that is not platform-independent
    (it won't be able to terminate timed-out processes on Windows). The fix is
    to not use shell=True in our call to Popen, but this would require changing
    the way we support test suite config files and this (large) change will
    have to wait.

    Some of the code in this class is based on ideas/code from QIIME's
    qiime.util.qiime_system_call function and the following posts:
        http://stackoverflow.com/a/4825933
        http://stackoverflow.com/a/4791612
    """

    def __init__(self, cmds, log_f, stop_on_first_failure=False,
                 log_individual_cmds=False):
        """Initializes a new object to execute multiple commands.

        Arguments:
            cmds - list of commands to run (strings)
            log_f - the file to write command output to
            stop_on_first_failure - if True, will stop running all other
                commands once a command has a nonzero exit code
            log_individual_cmds - if True, will create a TemporaryFile for each
                command that is run and log the output separately (as well as
                to log_f). Will also keep track of the return values for each
                command
        """
        self.cmds = cmds
        self.log_f = log_f
        self.stop_on_first_failure = stop_on_first_failure
        self.log_individual_cmds = log_individual_cmds

    def __call__(self, timeout):
        """Executes the commands within the given timeout, logging output.

        If this method is called multiple times using the same members, the
        output of the commands will be appended to the existing log_f.

        Returns a 2-element tuple where the first element is a logical, where
        True indicates all commands succeeded, False indicates at least one
        command failed, and None indicates a timeout occurred.

        The second element of the tuple will be an empty list if
        log_individual_cmds is False, otherwise will be filled with 2-element
        tuples containing the individual TemporaryFile log file for each
        command, and the command's return code.

        Arguments:
            timeout - the number of minutes to allow all of the commands (i.e.
                self.cmds)to run collectively before aborting and returning the
                current results. Must be a float, to allow for fractions of a
                minute
        """
        self._cmds_succeeded = True
        self._individual_cmds_status = []

        # We must create locks for the next two variables because they are
        # read/written in the main thread and worker thread. They allow
        # the threads to communicate when a timeout has occurred, and the
        # hung process that needs to be terminated.
        self._running_process = None
        self._running_process_lock = Lock()

        self._timeout_occurred = False
        self._timeout_occurred_lock = Lock()

        # Run the commands in a worker thread. Regain control after the
        # specified timeout.
        cmd_runner_thread = Thread(target=self._run_commands)
        cmd_runner_thread.start()
        cmd_runner_thread.join(float(timeout) * 60.0)

        if cmd_runner_thread.is_alive():
            # Timeout occurred, so terminate the current process and have the
            # worker thread exit gracefully.
            with self._timeout_occurred_lock:
                self._timeout_occurred = True

            with self._running_process_lock:
                if self._running_process is not None:
                    # We must kill the process group because the process was
                    # launched with a shell. This code won't work on Windows.
                    killpg(self._running_process.pid, SIGTERM)
            cmd_runner_thread.join()

        return self._cmds_succeeded, self._individual_cmds_status

    def _run_commands(self):
        """Code to be run in worker thread; actually executes the commands."""
        for cmd in self.cmds:
            # Check that there hasn't been a timeout before running the (next)
            # command.
            with self._timeout_occurred_lock:
                if self._timeout_occurred:
                    self._cmds_succeeded = None
                    break
                else:
                    with self._running_process_lock:
                        # setsid makes the spawned shell the process group
                        # leader, so that we can kill it and its children from
                        # the main thread.
                        proc = Popen(cmd, shell=True, universal_newlines=True,
                                     stdout=PIPE, stderr=PIPE,
                                     preexec_fn=setsid)
                        self._running_process = proc

            # Communicate pulls all stdout/stderr from the PIPEs to avoid
            # blocking-- don't remove this line! This call blocks until the
            # command finishes (or is terminated by the main thread).
            stdout, stderr = proc.communicate()
            ret_val = proc.returncode

            with self._running_process_lock:
                self._running_process = None

            cmd_str = 'Command:\n\n%s\n\n' % cmd
            stdout_str = 'Stdout:\n\n%s\n' % stdout
            stderr_str = 'Stderr:\n\n%s\n' % stderr
            self.log_f.write(cmd_str + stdout_str + stderr_str)

            if self.log_individual_cmds:
                individual_cmd_log_f = TemporaryFile(
                        prefix='clout_log', suffix='.txt')
                individual_cmd_log_f.write(cmd_str + stdout_str + stderr_str)
                self._individual_cmds_status.append(
                        (individual_cmd_log_f, ret_val))

            with self._timeout_occurred_lock:
                if ret_val != 0:
                    self._cmds_succeeded = False
                if self._timeout_occurred:
                    self._cmds_succeeded = None

                if self._timeout_occurred or \
                   (not self._cmds_succeeded and self.stop_on_first_failure):
                    break

def send_email(host, port, sender, password, recipients, subject, body,
               attachments=None):
    """Sends an email (optionally with attachments).

    This function does not return anything. It is not unit tested because it
    sends an actual email, and thus is difficult to test.

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
