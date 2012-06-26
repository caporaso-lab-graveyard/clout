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

"""Test suite for the email_test_results.py module."""

from cogent.util.unit_test import TestCase, main
from automated_testing.email_test_results import (_can_ignore,
        _build_email_summary, _get_num_failures, _parse_email_list,
        _parse_email_settings)

class EmailTestResultsTests(TestCase):
    """Tests for the email_test_results.py module."""

    def setUp(self):
        """Define some sample data that will be used by the tests."""
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

        # Standard email settings.
        self.email_settings1 = ["# A comment", "# Another comment",
                "\t  smtp_server some.smtp.server  \t ", "smtp_port 42",
                "sender foo@bar.baz", "password 424242!"]

        # Bad email settings.
        self.email_settings2 = ["# A comment", "", "  ", "\t\n",
                "smtp_server some.smtp.server", " ", "smtp_port\t42",
                "sender foo@bar.baz", "password 424242!"]

        # Pass.
        self.test_results1 = ["....", "--------------------------------------"
                "--------------------------------", "Ran 4 tests in 0.000s",
                "OK"]

        # Fail (single).
        self.test_results2 = ["E....", "==================================="
                "===================================", "ERROR: "
                "test_foo (__main__.FooTests)", "Test the foo.",
                "-------------------------------------------------------------"
                "---------", "Traceback (most recent call last):",
                "File 'tests/test_foo.py', line 42, in test_foo",
                "obs = get_foo(self.foo1)",
                "-------------------------------------------------------------"
                "---------", "Ran 5 tests in 0.001s", "", "FAILED (errors=1)"]

        # Fail (multiple).
        self.test_results3 = ["E....", "==================================="
                "===================================", "ERROR: "
                "test_foo (__main__.FooTests)", "Test the foo.",
                "-------------------------------------------------------------"
                "---------", "Traceback (most recent call last):",
                "File 'tests/test_foo.py', line 42, in test_foo",
                "obs = get_foo(self.foo1)",
                "-------------------------------------------------------------"
                "---------", "Ran 5 tests in 0.001s", "", "FAILED (errors=2)",
                "FAILED (failures=3)"]
        
        self.test_results_labels = ['QIIME', 'PyCogent']

    def test_parse_email_list_standard(self):
        """Test parsing a standard list of email addresses."""
        exp = ['foo@bar.baz', 'foo2@bar2.baz2']
        obs = _parse_email_list(self.email_list1)
        self.assertEqual(obs, exp)

    def test_parse_email_list_comments_only(self):
        """Test parsing a list containing only comments."""
        exp = []
        obs = _parse_email_list(self.email_list2)
        self.assertEqual(obs, exp)

    def test_parse_email_list_empty(self):
        """Test parsing an empty email list."""
        exp = []
        obs = _parse_email_list(self.email_list3)
        self.assertEqual(obs, exp)

    def test_parse_email_list_whitespace(self):
        """Test parsing a list of email addresses containing whitespace."""
        exp = ['foo@bar.baz', 'foo2@bar2.baz2']
        obs = _parse_email_list(self.email_list4)
        self.assertEqual(obs, exp)

    def test_parse_email_settings_standard(self):
        """Test parsing a standard email settings file."""
        exp = {'smtp_server': 'some.smtp.server', 'smtp_port': '42',
                'sender': 'foo@bar.baz', 'password': '424242!'}
        obs = _parse_email_settings(self.email_settings1)
        self.assertEqual(obs, exp)

    def test_parse_email_settings_invalid(self):
        """Test parsing an invalid email settings file."""
        self.assertRaises(ValueError,
                          _parse_email_settings, self.email_settings2)

    def test_build_email_summary_standard(self):
        """Test building an email body based on standard test results files."""
        exp = 'QIIME: Pass\nPyCogent: Fail (1 failure)\n'
        obs = _build_email_summary([self.test_results1, self.test_results2],
                                   self.test_results_labels)
        self.assertEqual(obs, exp)

    def test_build_email_summary_single(self):
        """Test building an email body based on a single test results file."""
        exp = 'foo: Pass\n'
        obs = _build_email_summary([self.test_results1], ['foo'])
        self.assertEqual(obs, exp)

    def test_build_email_summary_multi_failures(self):
        """Test building an email body based on multiple failures."""
        exp = 'foo: Fail (5 failures)\n'
        obs = _build_email_summary([self.test_results3], ['foo'])
        self.assertEqual(obs, exp)

    def test_build_email_summary_empty(self):
        """Test building an email body based on no test results files."""
        exp = ''
        obs = _build_email_summary([], [])
        self.assertEqual(obs, exp)

    def test_build_email_summary_invalid(self):
        """Test building email body based on wrong num of labels and files."""
        self.assertRaises(ValueError, _build_email_summary, [], ['foo'])
        self.assertRaises(ValueError, _build_email_summary,
                [self.test_results1], [])

    def test_get_num_failures_pass(self):
        """Test parsing test results that are a pass."""
        exp = 0
        obs = _get_num_failures(self.test_results1)
        self.assertEqual(obs, exp)

    def test_get_num_failures_fail(self):
        """Test parsing test results that are a fail."""
        exp = 1
        obs = _get_num_failures(self.test_results2)
        self.assertEqual(obs, exp)

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
