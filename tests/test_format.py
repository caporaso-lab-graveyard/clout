#!/usr/bin/env python
from __future__ import division

__author__ = "Jai Ram Rideout"
__copyright__ = "Copyright 2012-2013, The Clout Project"
__credits__ = ["Jai Ram Rideout"]
__license__ = "GPLv2"
__version__ = "0.9-dev"
__maintainer__ = "Jai Ram Rideout"
__email__ = "jai.rideout@gmail.com"

"""Test suite for the format.py module."""

from unittest import main, TestCase

from clout.format import format_email_summary

class FormatTests(TestCase):
    """Tests for the format.py module."""

    def test_format_email_summary_all_pass(self):
        """Test building an email body where all commands ran okay."""
        exp = 'QIIME: Pass\nPyCogent: Pass\n\n'
        obs = format_email_summary([('QIIME', 0), ('PyCogent', 0)])
        self.assertEqual(obs, exp)

    def test_format_email_summary_all_fail(self):
        """Test building an email body where all commands failed."""
        exp = 'QIIME: Fail\nPyCogent: Fail\n\n'
        obs = format_email_summary([('QIIME', 1), ('PyCogent', 77)])
        self.assertEqual(obs, exp)

    def test_format_email_summary_single_suite(self):
        """Test building an email body based on a single test suite."""
        exp = 'foo: Pass\n\n'
        obs = format_email_summary([('foo', 0)])
        self.assertEqual(obs, exp)

    def test_format_email_summary_empty(self):
        """Test building an email body based on no commands being run."""
        obs = format_email_summary([])
        self.assertEqual(obs, '')


if __name__ == "__main__":
    main()
