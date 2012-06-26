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

"""Contains functions used in the email_test_results.py script."""

from email.Encoders import encode_base64
from email.MIMEBase import MIMEBase
from email.MIMEMultipart import MIMEMultipart
from email.mime.text import MIMEText
from email.Utils import formatdate
from os.path import basename
from smtplib import SMTP

def email_test_results(test_results_files, test_results_fps,
                       test_results_labels, email_list_lines,
                       email_settings_lines):
    summary = _build_email_summary(test_results_files, test_results_labels)
    recipients = _parse_email_list(email_list_lines)
    settings = _parse_email_settings(email_settings_lines)
    _send_email(settings['smtp_server'], settings['smtp_port'],
                settings['sender'], settings['password'], recipients, summary,
                test_results_fps)

def _parse_email_list(email_list_lines):
    return [line.strip() for line in email_list_lines if not _can_ignore(line)]

def _parse_email_settings(email_settings_lines):
    settings = {}
    for line in email_settings_lines:
        if not _can_ignore(line):
            setting, val = line.strip().split(' ')
            settings[setting] = val
    return settings

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

def _get_num_failures(test_results_lines):
    failures = 0
    for line in test_results_lines:
        line = line.strip()
        if line.startswith('FAILED ('):
            failures += int(line.split('=')[1][:-1])
    return failures

def _can_ignore(line):
    return False if line.strip() != '' and not line.strip().startswith('#') \
           else True
