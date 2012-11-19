#!/usr/bin/env python
from __future__ import division

__author__ = "Jai Ram Rideout"
__copyright__ = "Copyright 2012, The Clout Project"
__credits__ = ["Jai Ram Rideout"]
__license__ = "GPL"
__version__ = "0.9-dev"
__maintainer__ = "Jai Ram Rideout"
__email__ = "jai.rideout@gmail.com"
__status__ = "Development"

"""Test suite for the run.py module."""

from re import sub
from unittest import main, TestCase

from clout.parse import parse_config_file
from clout.run import (_build_test_execution_commands,
                       _execute_commands_and_build_email, run_test_suites)

class RunTests(TestCase):
    """Tests for the run.py module."""

    def setUp(self):
        """Define some sample data that will be used by the tests."""
        # Standard config file with two test suites.
        self.config = ["# a comment", " ",
                "QIIME\tsource /bin/setup.sh; cd /bin; ./tests.py",
                "PyCogent\t/bin/cogent_tests"]

    def test_run_test_suites_invalid_input(self):
        """Test passing in bad input to run_test_suites()."""
        # Just use placeholders as input. We are only concerned with invalid
        # timeouts.
        self.assertRaises(ValueError, run_test_suites, 1, 1, 1, 1, 1, 1, 1, 10,
                0, 20)
        self.assertRaises(ValueError, run_test_suites, 1, 1, 1, 1, 1, 1, 1, -1,
                0, 0)

    def test_build_test_execution_commands_standard(self):
        """Test building commands based on standard, valid input."""
        exp = (["starcluster -c sc_config start nightly_tests"],
               ["starcluster -c sc_config sshmaster -u ubuntu nightly_tests "
                "'source /bin/setup.sh; cd /bin; ./tests.py'",
               "starcluster -c sc_config sshmaster -u ubuntu nightly_tests "
               "'/bin/cogent_tests'"],
               ["starcluster -c sc_config terminate -c nightly_tests"])

        test_suites = parse_config_file(self.config)
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

        test_suites = parse_config_file(self.config)
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

        test_suites = parse_config_file(self.config)
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
        self.assertEqual(name, 'complete_log.txt')
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
        self.assertEqual(name, 'complete_log.txt')

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
        self.assertEqual(name, 'complete_log.txt')
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
        self.assertEqual(name, 'complete_log.txt')
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
        self.assertEqual(name, 'complete_log.txt')
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
        self.assertEqual(name, 'complete_log.txt')
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
        self.assertEqual(name, 'complete_log.txt')
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
        self.assertEqual(name, 'complete_log.txt')
        self.assertEqual(log_f.read(),
            "Command:\n\necho setting up\n\nStdout:\n\nsetting up\n\nStderr:\n"
            "\n\nCommand:\n\necho foo\n\nStdout:\n\nfoo\n\nStderr:\n\n\n"
            "Command:\n\necho tearing down && sleep 5\n\nStdout:\n\ntearing "
            "down\n\nStderr:\n\n\n")

        name, log_f = obs[1][1]
        self.assertEqual(name, 'Test1_results.txt')
        self.assertEqual(log_f.read(),
            "Command:\n\necho foo\n\nStdout:\n\nfoo\n\nStderr:\n\n\n")


if __name__ == "__main__":
    main()
