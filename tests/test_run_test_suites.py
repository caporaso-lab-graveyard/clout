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

from re import sub
from tempfile import TemporaryFile
from unittest import main, TestCase

from automated_testing.run_test_suites import (_build_email_summary,
        _build_test_execution_commands, _can_ignore, _execute_commands,
        _execute_commands_and_build_email, _parse_config_file,
        _parse_email_list, _parse_email_settings, run_test_suites)

class RunTestSuitesTests(TestCase):
    """Tests for the run_test_suites.py module."""

    def setUp(self):
        """Define some sample data that will be used by the tests."""
        # The prefix to use for temporary files. This prefix may be added to,
        # but all temp files created by the tests will have this prefix at a
        # minimum.
        self.prefix = 'automated_testing_system_temp_file_'

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

    def test_run_test_suites_invalid_input(self):
        """Test passing in bad input to run_test_suites()."""
        # Just use placeholders as input. We are only concerned with invalid
        # timeouts.
        self.assertRaises(ValueError, run_test_suites, 1, 1, 1, 1, 1, 1, 1, 10,
                0, 20)
        self.assertRaises(ValueError, run_test_suites, 1, 1, 1, 1, 1, 1, 1, -1,
                0, 0)

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
        exp = (["starcluster -c sc_config start nightly_tests"],
               ["starcluster -c sc_config sshmaster -u ubuntu nightly_tests "
                "'source /bin/setup.sh; cd /bin; ./tests.py'",
               "starcluster -c sc_config sshmaster -u ubuntu nightly_tests "
               "'/bin/cogent_tests'"],
               ["starcluster -c sc_config terminate -c nightly_tests"])

        test_suites = _parse_config_file(self.config1)
        obs = _build_test_execution_commands(test_suites, 'sc_config',
                'ubuntu', 'nightly_tests')
        self.assertEqual(obs, exp)

    def test_build_test_execution_commands_custom_cluster_template(self):
        """Test building commands using a non-default cluster template."""
        exp = (["starcluster -c sc_config start -c some_cluster_template "
                "nightly_tests"],
               ["starcluster -c sc_config sshmaster -u ubuntu nightly_tests "
                "'source /bin/setup.sh; cd /bin; ./tests.py'",
                "starcluster -c sc_config sshmaster -u ubuntu nightly_tests "
                "'/bin/cogent_tests'"],
               ["starcluster -c sc_config terminate -c nightly_tests"])

        test_suites = _parse_config_file(self.config1)
        obs = _build_test_execution_commands(test_suites, 'sc_config',
                'ubuntu', 'nightly_tests', 'some_cluster_template')
        self.assertEqual(obs, exp)

    def test_build_test_execution_commands_custom_starcluster_exe_fp(self):
        """Test building commands using a non-default starcluster exec."""
        exp = (["/usr/local/bin/starcluster -c sc_config start -c "
                "some_cluster_template nightly_tests"],
               ["/usr/local/bin/starcluster -c sc_config sshmaster -u ubuntu "
                "nightly_tests 'source /bin/setup.sh; cd /bin; ./tests.py'",
                "/usr/local/bin/starcluster -c sc_config sshmaster -u ubuntu "
                "nightly_tests '/bin/cogent_tests'"],
               ["/usr/local/bin/starcluster -c sc_config terminate -c "
                "nightly_tests"])

        test_suites = _parse_config_file(self.config1)
        obs = _build_test_execution_commands(test_suites, 'sc_config',
                'ubuntu', 'nightly_tests', 'some_cluster_template',
                '/usr/local/bin/starcluster')
        self.assertEqual(obs, exp)

    def test_build_test_execution_commands_no_test_suites(self):
        """Test building commands with no test suites."""
        exp = (["starcluster -c sc_config start nightly_tests"], [],
               ["starcluster -c sc_config terminate -c nightly_tests"])
        obs = _build_test_execution_commands([], 'sc_config', 'ubuntu',
                                             'nightly_tests')
        self.assertEqual(obs, exp)

    def test_execute_commands_and_build_email(self):
        """Test functions correctly using standard, valid input."""
        obs = _execute_commands_and_build_email(
            [['Test1', 'echo foo'], ['Test2', 'echo bar']],
            ['echo setting up', 'echo ...'],
            ['echo foo', 'echo bar'],
            ['echo tearing down', 'echo ...'],
            1, 1, 1, 'test-cluster-tag')
        self.assertEqual(obs[0], 'Test1: Pass\nTest2: Pass\n\n')

        self.assertEqual(len(obs[1]), 3)
        name, log_f = obs[1][0]
        self.assertEqual(name, 'automated_testing_log.txt')
        self.assertEqual(log_f.read(),
            "Command:\n\necho setting up\n\nStdout:\n\nsetting up\n\n"
            "Stderr:\n\n\n"
            "Command:\n\necho ...\n\nStdout:\n\n...\n\nStderr:\n\n\n"
            "Command:\n\necho foo\n\nStdout:\n\nfoo\n\nStderr:\n\n\n"
            "Command:\n\necho bar\n\nStdout:\n\nbar\n\nStderr:\n\n\n"
            "Command:\n\necho tearing down\n\nStdout:\n\ntearing down\n\n"
            "Stderr:\n\n\n"
            "Command:\n\necho ...\n\nStdout:\n\n...\n\nStderr:\n\n\n")

        name, log_f = obs[1][1]
        self.assertEqual(name, 'Test1_results.txt')
        self.assertEqual(log_f.read(),
            "Command:\n\necho foo\n\nStdout:\n\nfoo\n\nStderr:\n\n\n")

        name, log_f = obs[1][2]
        self.assertEqual(name, 'Test2_results.txt')
        self.assertEqual(log_f.read(),
            "Command:\n\necho bar\n\nStdout:\n\nbar\n\nStderr:\n\n\n")

    def test_execute_commands_and_build_email_failures(self):
        """Test functions correctly when a test suite fails."""
        obs = _execute_commands_and_build_email(
            [['Test1', 'foobarbaz']],
            ['echo setting up'],
            ['foobarbaz'],
            ['echo tearing down'],
            1, 1, 1, 'test-cluster-tag')
        self.assertEqual(obs[0], 'Test1: Fail\n\n')

        self.assertEqual(len(obs[1]), 2)
        name, log_f = obs[1][0]
        self.assertEqual(name, 'automated_testing_log.txt')

        # We can't directly test the error message returned by /bin/sh because
        # this will differ between platforms (tested on Mac OS X and Ubuntu).
        # So strip out the error message, but keep everything else.
        self.assertEqual(sub('Stderr:\n\n.*\n\n', 'Stderr:\n\n\n\n',
                             log_f.read()),
            "Command:\n\necho setting up\n\nStdout:\n\nsetting up\n\n"
            "Stderr:\n\n\n"
            "Command:\n\nfoobarbaz\n\nStdout:\n\n\nStderr:\n\n\n\n"
            "Command:\n\necho tearing down\n\nStdout:\n\ntearing down\n\n"
            "Stderr:\n\n\n")

        name, log_f = obs[1][1]
        self.assertEqual(name, 'Test1_results.txt')
        self.assertEqual(sub('Stderr:\n\n.*\n\n', 'Stderr:\n\n\n\n',
                             log_f.read()),
            "Command:\n\nfoobarbaz\n\nStdout:\n\n\nStderr:\n\n\n\n")

    def test_execute_commands_and_build_email_setup_failure(self):
        """Test functions correctly when a setup command fails."""
        obs = _execute_commands_and_build_email(
            [['Test1', 'echo foo']],
            ['foobarbaz', 'echo setting up'],
            ['echo foo'],
            ['echo tearing down'],
            1, 1, 1, 'test-cluster-tag')
        self.assertEqual(obs[0], 'There were problems in starting the remote '
        'cluster while preparing to execute the test suite(s). Please check '
        'the attached log for more details.\n\n')

        self.assertEqual(len(obs[1]), 1)
        name, log_f = obs[1][0]
        self.assertEqual(name, 'automated_testing_log.txt')
        self.assertEqual(sub('Stderr:\n\n.*\n\n', 'Stderr:\n\n\n\n',
                             log_f.read()),
            "Command:\n\nfoobarbaz\n\nStdout:\n\n\nStderr:\n\n\n\n"
            "Command:\n\necho tearing down\n\nStdout:\n\ntearing down\n\n"
            "Stderr:\n\n\n")

    def test_execute_commands_and_build_email_teardown_failure(self):
        """Test functions correctly when a teardown command fails."""
        obs = _execute_commands_and_build_email(
            [['Test1', 'echo foo']],
            ['foobarbaz', 'echo setting up'],
            ['echo foo'],
            ['foobarbaz'],
            1, 1, 1, 'test-cluster-tag')
        self.assertEqual(obs[0], "There were problems in starting the remote "
        "cluster while preparing to execute the test suite(s). Please check "
        "the attached log for more details.\n\nThere were problems in "
        "terminating the remote cluster. Please check the attached log for "
        "more details.\n\nIMPORTANT: You should check that the cluster "
        "labelled with the tag 'test-cluster-tag' was properly terminated. If "
        "not, you should manually terminate it.\n\n")

        self.assertEqual(len(obs[1]), 1)
        name, log_f = obs[1][0]
        self.assertEqual(name, 'automated_testing_log.txt')
        self.assertEqual(sub('Stderr:\n\n.*\n\n', 'Stderr:\n\n\n\n',
                             log_f.read()),
            "Command:\n\nfoobarbaz\n\nStdout:\n\n\nStderr:\n\n\n\n"
            "Command:\n\nfoobarbaz\n\nStdout:\n\n\nStderr:\n\n\n\n")

    def test_execute_commands_and_build_email_test_suite_timeout(self):
        """Test functions correctly when a test suite timeout occurs."""
        # Test a timeout that occurs in the first test suite to run.
        obs = _execute_commands_and_build_email(
            [['Test1', 'echo foo && sleep 5'], ['Test2', 'echo bar']],
            ['echo setting up'],
            ['echo foo && sleep 5', 'echo bar'],
            ['echo tearing down'],
            1, 0.01, 1, 'test-cluster-tag')
        self.assertEqual(obs[0], 'Test1: Fail\n\nThe maximum allowable time '
            'of 0.01 minute(s) for all test suites to run was exceeded. The '
            'timeout occurred while running the Test1 test suite. The '
            'following test suites were not tested: Test2\n\n')

        self.assertEqual(len(obs[1]), 2)
        name, log_f = obs[1][0]
        self.assertEqual(name, 'automated_testing_log.txt')
        self.assertEqual(log_f.read(),
            "Command:\n\necho setting up\n\nStdout:\n\nsetting up\n\n"
            "Stderr:\n\n\n"
            "Command:\n\necho foo && sleep 5\n\n"
            "Stdout:\n\nfoo\n\nStderr:\n\n\n"
            "Command:\n\necho tearing down\n\nStdout:\n\ntearing down\n\n"
            "Stderr:\n\n\n")

        name, log_f = obs[1][1]
        self.assertEqual(name, 'Test1_results.txt')
        self.assertEqual(log_f.read(),
            "Command:\n\necho foo && sleep 5\n\n"
            "Stdout:\n\nfoo\n\nStderr:\n\n\n")

        # Test a timeout that occurs in the last test suite to run.
        obs = _execute_commands_and_build_email(
            [['Test1', 'echo foo'], ['Test2', 'sleep 5 && echo bar']],
            ['echo setting up'],
            ['echo foo', 'sleep 5 && echo bar'],
            ['echo tearing down'],
            1, 0.01, 1, 'test-cluster-tag')
        self.assertEqual(obs[0], 'Test1: Pass\nTest2: Fail\n\nThe maximum '
            'allowable time of 0.01 minute(s) for all test suites to run was '
            'exceeded. The timeout occurred while running the Test2 test '
            'suite.')

        self.assertEqual(len(obs[1]), 3)
        name, log_f = obs[1][0]
        self.assertEqual(name, 'automated_testing_log.txt')
        self.assertEqual(log_f.read(),
            "Command:\n\necho setting up\n\nStdout:\n\nsetting up\n\n"
            "Stderr:\n\n\n"
            "Command:\n\necho foo\n\nStdout:\n\nfoo\n\nStderr:\n\n\n"
            "Command:\n\nsleep 5 && echo bar\n\nStdout:\n\n\nStderr:\n\n\n"
            "Command:\n\necho tearing down\n\nStdout:\n\ntearing down\n\n"
            "Stderr:\n\n\n")

        name, log_f = obs[1][1]
        self.assertEqual(name, 'Test1_results.txt')
        self.assertEqual(log_f.read(),
            "Command:\n\necho foo\n\nStdout:\n\nfoo\n\nStderr:\n\n\n")

        name, log_f = obs[1][2]
        self.assertEqual(name, 'Test2_results.txt')
        self.assertEqual(log_f.read(),
            "Command:\n\nsleep 5 && echo bar\n\nStdout:\n\n\nStderr:\n\n\n")

    def test_execute_commands_and_build_email_setup_timeout(self):
        """Test functions correctly when a setup timeout occurs."""
        obs = _execute_commands_and_build_email(
            [['Test1', 'echo foo']],
            ['echo setting up && sleep 5'],
            ['echo foo'],
            ['echo tearing down'],
            0.01, 1, 1, 'test-cluster-tag')
        self.assertEqual(obs[0], 'The maximum allowable cluster setup time of '
        '0.01 minute(s) was exceeded.\n\n')

        self.assertEqual(len(obs[1]), 1)
        name, log_f = obs[1][0]
        self.assertEqual(name, 'automated_testing_log.txt')
        self.assertEqual(log_f.read(),
            "Command:\n\necho setting up && sleep 5\n\nStdout:\n\nsetting up\n"
            "\nStderr:\n\n\nCommand:\n\necho tearing down\n\nStdout:\n\n"
            "tearing down\n\nStderr:\n\n\n")

    def test_execute_commands_and_build_email_teardown_timeout(self):
        """Test functions correctly when a teardown timeout occurs."""
        obs = _execute_commands_and_build_email(
            [['Test1', 'echo foo']],
            ['echo setting up'],
            ['echo foo'],
            ['echo tearing down && sleep 5'],
            1, 1, 0.01, 'test-cluster-tag')
        self.assertEqual(obs[0], "Test1: Pass\n\nThe maximum allowable "
        "cluster termination time of 0.01 minute(s) was exceeded.\n\n"
        "IMPORTANT: You should check that the cluster labelled with the tag "
        "'test-cluster-tag' was properly terminated. If not, you should "
        "manually terminate it.\n\n")

        self.assertEqual(len(obs[1]), 2)
        name, log_f = obs[1][0]
        self.assertEqual(name, 'automated_testing_log.txt')
        self.assertEqual(log_f.read(),
            "Command:\n\necho setting up\n\nStdout:\n\nsetting up\n\nStderr:\n"
            "\n\nCommand:\n\necho foo\n\nStdout:\n\nfoo\n\nStderr:\n\n\n"
            "Command:\n\necho tearing down && sleep 5\n\nStdout:\n\ntearing "
            "down\n\nStderr:\n\n\n")

        name, log_f = obs[1][1]
        self.assertEqual(name, 'Test1_results.txt')
        self.assertEqual(log_f.read(),
            "Command:\n\necho foo\n\nStdout:\n\nfoo\n\nStderr:\n\n\n")

    def test_execute_commands(self):
        """Test executing arbitrary commands and logging their output."""
        # All commands succeed.
        exp = (True, [])
        log_f = TemporaryFile(prefix=self.prefix, suffix='.txt')
        obs = _execute_commands(['echo foo', 'echo bar'], log_f, 1)
        self.assertEqual(obs, exp)

        exp = ("Command:\n\necho foo\n\nStdout:\n\nfoo\n\nStderr:\n\n\n"
               "Command:\n\necho bar\n\nStdout:\n\nbar\n\nStderr:\n\n\n")
        log_f.seek(0, 0)
        obs = log_f.read()
        self.assertEqual(obs, exp)

        # One command fails.
        exp = (False, [])
        log_f = TemporaryFile(prefix=self.prefix, suffix='.txt')
        obs = _execute_commands(['echo foo', 'foobarbaz'], log_f, 1)
        self.assertEqual(obs, exp)

        exp = ("Command:\n\necho foo\n\nStdout:\n\nfoo\n\nStderr:\n\n\n"
               "Command:\n\nfoobarbaz\n\nStdout:\n\n\nStderr:\n\n\n\n")
        log_f.seek(0, 0)

        obs = sub('Stderr:\n\n.*\n\n', 'Stderr:\n\n\n\n',
                             log_f.read())
        self.assertEqual(obs, exp)

    def test_execute_commands_stop_on_first_failure(self):
        """Test executing arbitrary commands and stopping on first failure."""
        # All commands succeed.
        exp = (True, [])
        log_f = TemporaryFile(prefix=self.prefix, suffix='.txt')
        obs = _execute_commands(['echo foo', 'echo bar'], log_f, 1, True)
        self.assertEqual(obs, exp)

        exp = ("Command:\n\necho foo\n\nStdout:\n\nfoo\n\nStderr:\n\n\n"
               "Command:\n\necho bar\n\nStdout:\n\nbar\n\nStderr:\n\n\n")
        log_f.seek(0, 0)
        obs = log_f.read()
        self.assertEqual(obs, exp)

        # First command fails.
        exp = (False, [])
        log_f = TemporaryFile(prefix=self.prefix, suffix='.txt')
        obs = _execute_commands(['foobarbaz', 'echo foo'], log_f, 1, True)
        self.assertEqual(obs, exp)

        exp = ("Command:\n\nfoobarbaz\n\nStdout:\n\n\nStderr:\n\n\n\n")
        log_f.seek(0, 0)
        obs = sub('Stderr:\n\n.*\n\n', 'Stderr:\n\n\n\n',
                             log_f.read())
        self.assertEqual(obs, exp)

        # Second command fails.
        exp = (False, [])
        log_f = TemporaryFile(prefix=self.prefix, suffix='.txt')
        obs = _execute_commands(['echo foo', 'foobarbaz'], log_f, 1, True)
        self.assertEqual(obs, exp)

        exp = ("Command:\n\necho foo\n\nStdout:\n\nfoo\n\nStderr:\n\n\n"
               "Command:\n\nfoobarbaz\n\nStdout:\n\n\nStderr:\n\n\n\n")
        log_f.seek(0, 0)
        obs = sub('Stderr:\n\n.*\n\n', 'Stderr:\n\n\n\n',
                             log_f.read())
        self.assertEqual(obs, exp)

    def test_execute_commands_log_individual_cmds(self):
        """execute arbitrary commands and log each one separately."""
        # All commands succeed.
        log_f = TemporaryFile(prefix=self.prefix, suffix='.txt')
        obs = _execute_commands(['echo foo', 'echo bar'], log_f, 1,
                                log_individual_cmds=True)
        self.assertEqual(obs[0], True)
        self.assertEqual(len(obs[1]), 2)
        self.assertEqual(obs[1][0][1], 0)
        self.assertEqual(obs[1][1][1], 0)

        exp = ("Command:\n\necho foo\n\nStdout:\n\nfoo\n\nStderr:\n\n\n"
               "Command:\n\necho bar\n\nStdout:\n\nbar\n\nStderr:\n\n\n")
        log_f.seek(0, 0)
        log_obs = log_f.read()
        self.assertEqual(log_obs, exp)

        exp = "Command:\n\necho foo\n\nStdout:\n\nfoo\n\nStderr:\n\n\n"
        log_f = obs[1][0][0]
        log_f.seek(0, 0)
        log_obs = log_f.read()
        self.assertEqual(log_obs, exp)

        exp = "Command:\n\necho bar\n\nStdout:\n\nbar\n\nStderr:\n\n\n"
        log_f = obs[1][1][0]
        log_f.seek(0, 0)
        log_obs = log_f.read()
        self.assertEqual(log_obs, exp)

        # First command fails.
        log_f = TemporaryFile(prefix=self.prefix, suffix='.txt')
        obs = _execute_commands(['foobarbaz', 'echo foo'], log_f, 1,
                                log_individual_cmds=True)
        self.assertEqual(obs[0], False)
        self.assertEqual(len(obs[1]), 2)
        self.assertEqual(obs[1][0][1], 127)
        self.assertEqual(obs[1][1][1], 0)

        exp = ("Command:\n\nfoobarbaz\n\nStdout:\n\n\nStderr:\n\n\n\n"
               "Command:\n\necho foo\n\nStdout:\n\nfoo\n\nStderr:\n\n\n")
        log_f.seek(0, 0)
        log_obs = sub('Stderr:\n\n.*\n\n', 'Stderr:\n\n\n\n',
                             log_f.read())
        self.assertEqual(log_obs, exp)

        exp = ("Command:\n\nfoobarbaz\n\nStdout:\n\n\nStderr:\n\n\n\n")
        log_f = obs[1][0][0]
        log_f.seek(0, 0)
        log_obs = sub('Stderr:\n\n.*\n\n', 'Stderr:\n\n\n\n',
                             log_f.read())
        self.assertEqual(log_obs, exp)

        exp = "Command:\n\necho foo\n\nStdout:\n\nfoo\n\nStderr:\n\n\n"
        log_f = obs[1][1][0]
        log_f.seek(0, 0)
        log_obs = log_f.read()
        self.assertEqual(log_obs, exp)

    def test_build_email_summary_all_pass(self):
        """Test building an email body where all commands ran okay."""
        exp = 'QIIME: Pass\nPyCogent: Pass\n\n'
        obs = _build_email_summary([('QIIME', 0), ('PyCogent', 0)])
        self.assertEqual(obs, exp)

    def test_build_email_summary_all_fail(self):
        """Test building an email body where all commands failed."""
        exp = 'QIIME: Fail\nPyCogent: Fail\n\n'
        obs = _build_email_summary([('QIIME', 1), ('PyCogent', 77)])
        self.assertEqual(obs, exp)

    def test_build_email_summary_single_suite(self):
        """Test building an email body based on a single test suite."""
        exp = 'foo: Pass\n\n'
        obs = _build_email_summary([('foo', 0)])
        self.assertEqual(obs, exp)

    def test_build_email_summary_empty(self):
        """Test building an email body based on no commands being run."""
        obs = _build_email_summary([])
        self.assertEqual(obs, '')

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
