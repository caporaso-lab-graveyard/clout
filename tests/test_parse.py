#!/usr/bin/env python
from __future__ import division

__author__ = "Jai Ram Rideout"
__copyright__ = "Copyright 2012-2013, The Clout Project"
__credits__ = ["Jai Ram Rideout"]
__license__ = "GPLv2"
__version__ = "0.9-dev"
__maintainer__ = "Jai Ram Rideout"
__email__ = "jai.rideout@gmail.com"

"""Test suite for the parse.py module."""

from unittest import main, TestCase

from clout.parse import (parse_config_file, parse_email_list,
                         parse_email_settings, _can_ignore)

class ParseTests(TestCase):
    """Tests for the parse.py module."""

    def setUp(self):
        """Define some sample data that will be used by the tests."""
        # Standard config file with two test suites.
        self.config1 = ["# a comment", " ",
                "QIIME\tsource /bin/setup.sh; cd /bin; ./tests.py",
                "PyCogent\t/bin/cogent_tests"]

        # An empty config.
        self.config2 = ["# a comment", " ", "\n\t\t\t\t"]

        # An incorrectly-formatted config file (not the right number of
        # fields).
        self.config3 = ["# a comment", "QIIME\t/bin/tests.py", "PyCogent"]

        # Non-unique test suite labels.
        self.config4 = ["# a comment", "QIIME\t/bin/tests.py",
                        "PyCogent\t/foo.py", "QIIME\t/bar/baz.sh"]

        # Empty fields.
        self.config5 = ["QIIME\t/bin/tests.py", "\t/bin/foo.sh"]

        # Standard email list with a comment.
        self.email_list1 = ["# some comment...", "foo@bar.baz",
                            "foo2@bar2.baz2"]

        # Email list only containing comments.
        self.email_list2 = [" \t# some comment...", "#foo@bar.baz"]

        # Empty list.
        self.email_list3 = []

        # List with addresses containing whitespace before and after.
        self.email_list4 = ["\tfoo@bar.baz  ", "\n\t  foo2@bar2.baz2\t ",
                            "\t   \n\t"]

        # List containing invalid email addresses.
        self.email_list5 = ["# a comment...", "foo@bar.baz", "foo.bar.baz"]

        # Standard email settings.
        self.email_settings1 = ["# A comment", "# Another comment",
                "smtp_server\tsome.smtp.server", "smtp_port\t42",
                "sender\tfoo@bar.baz", "password\t424242!"]

        # Bad email settings (no tab).
        self.email_settings2 = ["# A comment", "", "  ", "\t\n",
                "smtp_server some.smtp.server", " ", "smtp_port\t42",
                "sender foo@bar.baz", "password 424242!"]

        # Bad email settings (too many fields).
        self.email_settings3 = ["# A comment", "", "  ", "\t\n",
                "smtp_server\tsome.smtp.server\tfoo", " ", "smtp_port\t42",
                "sender foo@bar.baz", "password 424242!"]

        # Bad email settings (unrecognized setting).
        self.email_settings4 = ["# A comment", "smtp_server\tfoo.bar.com",
                                "stmp_port\t44"]

        # Bad email settings (missing required settings).
        self.email_settings5 = ["# A comment", "smtp_server\tfoo.bar.com",
                                "smtp_port\t44"]

    def test_parse_config_file_standard(self):
        """Test parsing a standard config file."""
        exp = [['QIIME', 'source /bin/setup.sh; cd /bin; ./tests.py'],
               ['PyCogent', '/bin/cogent_tests']]
        obs = parse_config_file(self.config1)
        self.assertEqual(obs, exp)

    def test_parse_config_file_empty(self):
        """Test parsing an empty config file."""
        self.assertRaises(ValueError, parse_config_file, self.config2)

    def test_parse_config_file_invalid(self):
        """Test parsing an incorrectly-formatted config file."""
        self.assertRaises(ValueError, parse_config_file, self.config3)

    def test_parse_config_file_nonunique_labels(self):
        """Test parsing an config file with non-unique labels."""
        self.assertRaises(ValueError, parse_config_file, self.config4)

    def test_parse_config_file_empty_fields(self):
        """Test parsing an config file with empty fields."""
        self.assertRaises(ValueError, parse_config_file, self.config5)

    def test_parse_email_list_standard(self):
        """Test parsing a standard list of email addresses."""
        exp = ['foo@bar.baz', 'foo2@bar2.baz2']
        obs = parse_email_list(self.email_list1)
        self.assertEqual(obs, exp)

    def test_parse_email_list_empty(self):
        """Test parsing a list containing only comments or completely empty."""
        self.assertRaises(ValueError, parse_email_list, self.email_list2)
        self.assertRaises(ValueError, parse_email_list, self.email_list3)

    def test_parse_email_list_whitespace(self):
        """Test parsing a list of email addresses containing whitespace."""
        exp = ['foo@bar.baz', 'foo2@bar2.baz2']
        obs = parse_email_list(self.email_list4)
        self.assertEqual(obs, exp)

    def test_parse_email_list_bad_address(self):
        """Test parsing a list containing an invalid email address."""
        self.assertRaises(ValueError, parse_email_list, self.email_list5)

    def test_parse_email_settings_standard(self):
        """Test parsing a standard email settings file."""
        exp = {'smtp_server': 'some.smtp.server', 'smtp_port': '42',
                'sender': 'foo@bar.baz', 'password': '424242!'}
        obs = parse_email_settings(self.email_settings1)
        self.assertEqual(obs, exp)

    def test_parse_email_settings_invalid(self):
        """Test parsing invalid email settings files."""
        self.assertRaises(ValueError,
                          parse_email_settings, self.email_settings2)
        self.assertRaises(ValueError,
                          parse_email_settings, self.email_settings3)
        self.assertRaises(ValueError,
                          parse_email_settings, self.email_settings4)
        self.assertRaises(ValueError,
                          parse_email_settings, self.email_settings5)

    def test_can_ignore(self):
        """Test whether comments and whitespace-only lines are ignored."""
        self.assertEqual(_can_ignore(self.email_list1[0]), True)
        self.assertEqual(_can_ignore(self.email_list1[1]), False)
        self.assertEqual(_can_ignore(self.email_list1[2]), False)
        self.assertEqual(_can_ignore(self.email_list2[0]), True)
        self.assertEqual(_can_ignore(self.email_list2[1]), True)
        self.assertEqual(_can_ignore(self.email_list4[0]), False)
        self.assertEqual(_can_ignore(self.email_list4[1]), False)
        self.assertEqual(_can_ignore(self.email_list4[2]), True)


if __name__ == "__main__":
    main()
