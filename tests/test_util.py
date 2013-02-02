#!/usr/bin/env python
from __future__ import division

__author__ = "Jai Ram Rideout"
__copyright__ = "Copyright 2012-2013, The Clout Project"
__credits__ = ["Jai Ram Rideout"]
__license__ = "GPLv2"
__version__ = "0.9-dev"
__maintainer__ = "Jai Ram Rideout"
__email__ = "jai.rideout@gmail.com"

"""Test suite for the util.py module."""

from re import sub
from tempfile import TemporaryFile
from unittest import main, TestCase

from clout.util import CommandExecutor

class UtilTests(TestCase):
    """Tests for the util.py module."""

    def setUp(self):
        """Define some sample data that will be used by the tests."""
        # The prefix to use for temporary files. This prefix may be added to,
        # but all temp files created by the tests will have this prefix at a
        # minimum.
        self.prefix = 'clout_temp_file_'

    def test_CommandExecutor(self):
        """Test executing arbitrary commands and logging their output."""
        # All commands succeed.
        exp = (True, [])
        log_f = TemporaryFile(prefix=self.prefix, suffix='.txt')
        cmd_exec = CommandExecutor(['echo foo', 'echo bar'], log_f)
        obs = cmd_exec(1)
        self.assertEqual(obs, exp)

        exp = ("Command:\n\necho foo\n\nStdout:\n\nfoo\n\nStderr:\n\n\n"
               "Command:\n\necho bar\n\nStdout:\n\nbar\n\nStderr:\n\n\n")
        log_f.seek(0, 0)
        obs = log_f.read()
        self.assertEqual(obs, exp)

        # One command fails.
        exp = (False, [])
        log_f = TemporaryFile(prefix=self.prefix, suffix='.txt')
        cmd_exec = CommandExecutor(['echo foo', 'foobarbaz'], log_f)
        obs = cmd_exec(1)
        self.assertEqual(obs, exp)

        exp = ("Command:\n\necho foo\n\nStdout:\n\nfoo\n\nStderr:\n\n\n"
               "Command:\n\nfoobarbaz\n\nStdout:\n\n\nStderr:\n\n\n\n")
        log_f.seek(0, 0)

        obs = sub('Stderr:\n\n.*\n\n', 'Stderr:\n\n\n\n', log_f.read())
        self.assertEqual(obs, exp)

    def test_CommandExecutor_stop_on_first_failure(self):
        """Test executing arbitrary commands and stopping on first failure."""
        # All commands succeed.
        exp = (True, [])
        log_f = TemporaryFile(prefix=self.prefix, suffix='.txt')
        cmd_exec = CommandExecutor(['echo foo', 'echo bar'], log_f,
                                   stop_on_first_failure=True)
        obs = cmd_exec(1)
        self.assertEqual(obs, exp)

        exp = ("Command:\n\necho foo\n\nStdout:\n\nfoo\n\nStderr:\n\n\n"
               "Command:\n\necho bar\n\nStdout:\n\nbar\n\nStderr:\n\n\n")
        log_f.seek(0, 0)
        obs = log_f.read()
        self.assertEqual(obs, exp)

        # First command fails.
        exp = (False, [])
        log_f = TemporaryFile(prefix=self.prefix, suffix='.txt')
        cmd_exec = CommandExecutor(['foobarbaz', 'echo foo'], log_f,
                                   stop_on_first_failure=True)
        obs = cmd_exec(1)
        self.assertEqual(obs, exp)

        exp = ("Command:\n\nfoobarbaz\n\nStdout:\n\n\nStderr:\n\n\n\n")
        log_f.seek(0, 0)
        obs = sub('Stderr:\n\n.*\n\n', 'Stderr:\n\n\n\n',
                             log_f.read())
        self.assertEqual(obs, exp)

        # Second command fails.
        exp = (False, [])
        log_f = TemporaryFile(prefix=self.prefix, suffix='.txt')
        cmd_exec = CommandExecutor(['echo foo', 'foobarbaz'], log_f,
                                   stop_on_first_failure=True)
        obs = cmd_exec(1)
        self.assertEqual(obs, exp)

        exp = ("Command:\n\necho foo\n\nStdout:\n\nfoo\n\nStderr:\n\n\n"
               "Command:\n\nfoobarbaz\n\nStdout:\n\n\nStderr:\n\n\n\n")
        log_f.seek(0, 0)
        obs = sub('Stderr:\n\n.*\n\n', 'Stderr:\n\n\n\n',
                             log_f.read())
        self.assertEqual(obs, exp)

    def test_CommandExecutor_log_individual_cmds(self):
        """execute arbitrary commands and log each one separately."""
        # All commands succeed.
        log_f = TemporaryFile(prefix=self.prefix, suffix='.txt')
        cmd_exec = CommandExecutor(['echo foo', 'echo bar'], log_f,
                                   log_individual_cmds=True)
        obs = cmd_exec(1)
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
        cmd_exec = CommandExecutor(['foobarbaz', 'echo foo'], log_f,
                                   log_individual_cmds=True)
        obs = cmd_exec(1)
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


if __name__ == "__main__":
    main()
