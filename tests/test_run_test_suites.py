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

"""Test suite for the run_test_suites.py module."""

from cogent.util.unit_test import TestCase, main
from automated_testing.run_test_suites import (_build_email_summary,
        _build_test_execution_commands, _can_ignore, _get_num_failures,
        _parse_config_file, _parse_email_list, _parse_email_settings)

class RunTestSuitesTests(TestCase):
    """Tests for the run_test_suites.py module."""

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

    def test_parse_config_file_standard(self):
        """Test parsing a standard config file."""
        exp = [['QIIME', 'source /bin/setup.sh; cd /bin; ./tests.py'],
               ['PyCogent', '/bin/cogent_tests']]
        obs = _parse_config_file(self.config1)
        self.assertEqual(obs, exp)

    def test_parse_config_file_empty(self):
        """Test parsing an empty config file."""
        self.assertRaises(ValueError, _parse_config_file, self.config2)

    def test_parse_config_file_invalid(self):
        """Test parsing an incorrectly-formatted config file."""
        self.assertRaises(ValueError, _parse_config_file, self.config3)

    def test_parse_config_file_nonunique_labels(self):
        """Test parsing an config file with non-unique labels."""
        self.assertRaises(ValueError, _parse_config_file, self.config4)

    def test_parse_config_file_empty_fields(self):
        """Test parsing an config file with empty fields."""
        self.assertRaises(ValueError, _parse_config_file, self.config5)

    def test_parse_email_list_standard(self):
        """Test parsing a standard list of email addresses."""
        exp = ['foo@bar.baz', 'foo2@bar2.baz2']
        obs = _parse_email_list(self.email_list1)
        self.assertEqual(obs, exp)

    def test_parse_email_list_empty(self):
        """Test parsing a list containing only comments or completely empty."""
        self.assertRaises(ValueError, _parse_email_list, self.email_list2)
        self.assertRaises(ValueError, _parse_email_list, self.email_list3)

    def test_parse_email_list_whitespace(self):
        """Test parsing a list of email addresses containing whitespace."""
        exp = ['foo@bar.baz', 'foo2@bar2.baz2']
        obs = _parse_email_list(self.email_list4)
        self.assertEqual(obs, exp)

    def test_parse_email_list_bad_address(self):
        """Test parsing a list containing an invalid email address."""
        self.assertRaises(ValueError, _parse_email_list, self.email_list5)

    def test_parse_email_settings_standard(self):
        """Test parsing a standard email settings file."""
        exp = {'smtp_server': 'some.smtp.server', 'smtp_port': '42',
                'sender': 'foo@bar.baz', 'password': '424242!'}
        obs = _parse_email_settings(self.email_settings1)
        self.assertEqual(obs, exp)

    def test_parse_email_settings_invalid(self):
        """Test parsing invalid email settings files."""
        self.assertRaises(ValueError,
                          _parse_email_settings, self.email_settings2)
        self.assertRaises(ValueError,
                          _parse_email_settings, self.email_settings3)
        self.assertRaises(ValueError,
                          _parse_email_settings, self.email_settings4)
        self.assertRaises(ValueError,
                          _parse_email_settings, self.email_settings5)

    def test_build_test_execution_commands_standard(self):
        """Test building commands based on standard, valid input."""
        exp = [(None, "starcluster -c sc_config start nightly_tests"),
               ('QIIME', "starcluster -c sc_config sshmaster -u ubuntu "
               "nightly_tests 'source /bin/setup.sh; cd /bin; ./tests.py'"),
               ('PyCogent', "starcluster -c sc_config sshmaster -u ubuntu "
               "nightly_tests '/bin/cogent_tests'"),
               (None, 'starcluster -c sc_config terminate -c nightly_tests')]

        test_suites = _parse_config_file(self.config1)
        obs = _build_test_execution_commands(test_suites, 'sc_config',
                'ubuntu', 'nightly_tests')
        self.assertEqual(obs, exp)

    def test_build_test_execution_commands_custom_cluster_template(self):
        """Test building commands using a non-default cluster template."""
        exp = [(None, "starcluster -c sc_config start -c "
                "some_cluster_template nightly_tests"),
               ('QIIME', "starcluster -c sc_config sshmaster -u ubuntu "
               "nightly_tests 'source /bin/setup.sh; cd /bin; ./tests.py'"),
               ('PyCogent', "starcluster -c sc_config sshmaster -u ubuntu "
               "nightly_tests '/bin/cogent_tests'"),
               (None, 'starcluster -c sc_config terminate -c nightly_tests')]

        test_suites = _parse_config_file(self.config1)
        obs = _build_test_execution_commands(test_suites, 'sc_config',
                'ubuntu', 'nightly_tests', 'some_cluster_template')
        self.assertEqual(obs, exp)

    def test_build_test_execution_commands_no_test_suites(self):
        """Test building commands with no test suites."""
        exp = [(None, "starcluster -c sc_config start nightly_tests"),
               (None, 'starcluster -c sc_config terminate -c nightly_tests')]
        obs = _build_test_execution_commands([], 'sc_config', 'ubuntu',
                                             'nightly_tests')
        self.assertEqual(obs, exp)

    def test_build_email_summary_standard(self):
        """Test building an email body based on standard test results files."""
        exp = 'QIIME: Pass\nPyCogent: Fail (1 failure)\n'
        obs = _build_email_summary([('QIIME', 'QIIME_results.txt',
                                     self.test_results1), ('PyCogent',
                                     'PyCogent_results.txt',
                                     self.test_results2), (None, 'log.txt',
                                     self.test_results2)])
        self.assertEqual(obs, exp)

    def test_build_email_summary_single(self):
        """Test building an email body based on a single test results file."""
        exp = 'foo: Pass\n'
        obs = _build_email_summary([('foo', 'foo_results.txt',
                                     self.test_results1)])
        self.assertEqual(obs, exp)

    def test_build_email_summary_multi_failures(self):
        """Test building an email body based on multiple failures."""
        exp = 'foo: Fail (5 failures)\n'
        obs = _build_email_summary([('foo', 'foo_results.txt',
                                     self.test_results3)])
        self.assertEqual(obs, exp)

    def test_build_email_summary_empty(self):
        """Test building an email body based on no test results files."""
        obs = _build_email_summary([])
        self.assertEqual(obs, '')

    def test_build_email_summary_all_logs(self):
        """Test building email body based on only log files (no test suite)."""
        obs = _build_email_summary([(None, 'QIIME_results.txt',
                                     self.test_results1),
                                    (None, 'PyCogent_results.txt',
                                     self.test_results2),
                                    (None, 'log.txt',
                                     self.test_results2)])
        self.assertEqual(obs, '')

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
