# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
"""
Tests for the pulp.server.async.manage_workers module.
"""
import os
import subprocess
import unittest

import mock

from pulp.server.async import manage_workers


class TestGetConcurrency(unittest.TestCase):
    """
    Test the _get_concurrency() function.
    """
    @mock.patch('pulp.server.async.manage_workers.multiprocessing.cpu_count', return_value=16)
    @mock.patch('pulp.server.async.manage_workers.subprocess.Popen')
    def test_concurrency_not_set(self, Popen, cpu_count):
        """
        Test for the case where PULP_CONCURRENCY is not set in /etc/default/pulp_workers.
        """
        class MockPipe(object):
            def communicate(self):
                """
                Return \n as the output of the subprocess, to simulate PULP_CONCURRENCY not being
                defined.
                """
                return ('\n',)
        Popen.return_value = MockPipe()

        concurrency = manage_workers._get_concurrency()

        # Since we mocked the cpu_count to be 16, concurrency should be 16
        self.assertEqual(concurrency, 16)
        # Make sure that Popen and cpu_count were called correctly
        Popen.assert_called_once_with(
            '. %s; echo $PULP_CONCURRENCY' % manage_workers._ENVIRONMENT_FILE,
            stdout=subprocess.PIPE, shell=True)
        cpu_count.assert_called_once_with()

    @mock.patch('pulp.server.async.manage_workers.multiprocessing.cpu_count', return_value=16)
    @mock.patch('pulp.server.async.manage_workers.subprocess.Popen')
    def test_concurrency_set(self, Popen, cpu_count):
        """
        Test for the case where PULP_CONCURRENCY is set in /etc/default/pulp_workers.
        """
        class MockPipe(object):
            def communicate(self):
                """
                Return 32\n as the output of the subprocess, to simulate PULP_CONCURRENCY being
                defined as 32.
                """
                return ('32\n',)
        Popen.return_value = MockPipe()

        concurrency = manage_workers._get_concurrency()

        # Since we mocked the output of the subprocess call to be 32\n, concurrency should be 32
        self.assertEqual(concurrency, 32)
        # Make sure that Popen was called correctly
        Popen.assert_called_once_with(
            '. %s; echo $PULP_CONCURRENCY' % manage_workers._ENVIRONMENT_FILE,
            stdout=subprocess.PIPE, shell=True)
        # Since the shell call was successful, no call to cpu_count() should have been made
        self.assertEqual(cpu_count.call_count, 0)


class TestGetFileContents(unittest.TestCase):
    """
    Test the _get_file_contents() function.
    """
    def test__get_file_contents(self):
        """
        Simple test of _get_file_contents, mocking the open() call.
        """
        file_contents = 'Some contents.'

        with mock.patch('__builtin__.open', autospec=True) as mock_open:
            mock_file = mock.MagicMock(spec=file)
            mock_file.read.return_value = file_contents
            mock_context = mock.MagicMock()
            mock_context.__enter__.return_value = mock_file
            mock_open.return_value = mock_context
            contents = manage_workers._get_file_contents('/some/path')

        self.assertEqual(contents, file_contents)
        mock_open.assert_called_once_with('/some/path')
        # Make sure the file handle was treated properly
        file_context = mock_open()
        file_context.__enter__.assert_called_once_with()
        file_handle = file_context.__enter__()
        file_handle.read.assert_called_once_with()
        file_context.__exit__.assert_called_once_with(None, None, None)


class TestMain(unittest.TestCase):
    """
    Test the main() function.
    """
    @mock.patch('pulp.server.async.manage_workers._start_workers')
    @mock.patch('pulp.server.async.manage_workers.sys.argv',
                ('/usr/libexec/pulp-manage-workers', 'start'))
    def test_start(self, _start_workers):
        """
        Test with "start" as an arg.
        """
        manage_workers.main()

        _start_workers.assert_called_once_with()

    @mock.patch('pulp.server.async.manage_workers._stop_workers')
    @mock.patch('pulp.server.async.manage_workers.sys.argv',
                ('/usr/libexec/pulp-manage-workers', 'stop'))
    def test_stop(self, _stop_workers):
        """
        Test with "stop" as an arg.
        """
        manage_workers.main()

        _stop_workers.assert_called_once_with()

    @mock.patch('pulp.server.async.manage_workers.sys.argv',
                ('/usr/libexec/pulp-manage-workers', 'not_valid'))
    @mock.patch('pulp.server.async.manage_workers.sys.exit')
    @mock.patch('sys.stderr')
    def test_wrong_arg(self, stderr, exit):
        """
        Test with an argument that isn't "stop" or "start".
        """
        manage_workers.main()

        error_msg = 'This script may only be called with "start" or "stop" as an argument.\n'
        stderr.write.assert_called_once_with(error_msg)
        exit.assert_called_once_with(1)

    @mock.patch('pulp.server.async.manage_workers.sys.argv',
                ('/usr/libexec/pulp-manage-workers',))
    @mock.patch('pulp.server.async.manage_workers.sys.exit')
    @mock.patch('sys.stderr')
    def test_wrong_num_args(self, stderr, exit):
        """
        Test for the case when the wrong number of args are passed.
        """
        # We need sys.exit to have this Exception as a side effect, because we'll get an IndexError
        # when main() tries to access sys.argv[1] if we don't have sys.exit() halt execution of
        # main().
        class SysExit(Exception):
            pass
        exit.side_effect = SysExit()

        self.assertRaises(SysExit, manage_workers.main)

        error_msg = 'This script may only be called with "start" or "stop" as an argument.\n'
        stderr.write.assert_called_once_with(error_msg)
        exit.assert_called_once_with(1)


class TestStartWorkers(unittest.TestCase):
    """
    Test the _start_workers() function. For simplicity, these tests all set concurrency to 1.
    """
    @mock.patch('pulp.server.async.manage_workers._get_concurrency', mock.MagicMock(return_value=1))
    @mock.patch('pulp.server.async.manage_workers.os.path.exists',
                mock.MagicMock(return_value=True))
    @mock.patch('pulp.server.async.manage_workers.subprocess.Popen')
    @mock.patch('pulp.server.async.manage_workers.sys.exit')
    @mock.patch('sys.stderr')
    @mock.patch('sys.stdout')
    def test_systemctl_non_zero_exit_code(self, stdout, stderr, exit, Popen):
        """
        _start_workers() uses systemctl. This test ensures that a non-zero exit code from systemctl
        is handled appropriately.
        """
        class SysExit(Exception):
            pass
        exit.side_effect = SysExit()
        pipe_output = ('some output', 'some errors')
        Popen.return_value = mock.MagicMock()
        Popen.return_value.returncode = 42
        Popen.return_value.communicate.return_value = pipe_output
        expected_read_data = manage_workers._WORKER_TEMPLATE % {
            'num': 0, 'environment_file': manage_workers._ENVIRONMENT_FILE}

        with mock.patch('__builtin__.open', autospec=True) as mock_open:
            mock_file = mock.MagicMock(spec=file)
            mock_file.read.return_value = expected_read_data
            mock_context = mock.MagicMock()
            mock_context.__enter__.return_value = mock_file
            mock_open.return_value = mock_context
            self.assertRaises(SysExit, manage_workers._start_workers)

        # Make sure open was called correctly
        unit_filename = manage_workers._UNIT_FILENAME_TEMPLATE % 0
        expected_path = os.path.join(manage_workers._SYSTEMD_UNIT_PATH, unit_filename)
        mock_open.assert_called_once_with(expected_path)
        file_context = mock_open()
        file_context.__enter__.assert_called_once_with()
        file_handle = file_context.__enter__()
        file_handle.read.assert_called_once_with()
        file_context.__exit__.assert_called_once_with(None, None, None)

        # Make sure we started the worker correctly
        Popen.assert_called_once_with('systemctl start %s' % unit_filename, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, shell=True)
        pipe = Popen()
        pipe.communicate.assert_called_once_with()

        # Make sure we printed the output of the pipe
        self.assertEqual(stdout.write.call_count, 2)
        self.assertEqual(stdout.write.mock_calls[0][1][0], pipe_output[0])
        self.assertEqual(stdout.write.mock_calls[1][1][0], '\n')
        # And the errors
        self.assertEqual(stderr.write.call_count, 1)
        self.assertEqual(stderr.write.mock_calls[0][1][0], pipe_output[1])
        # Make sure the exit code was passed on
        exit.assert_called_once_with(42)

    @mock.patch('pulp.server.async.manage_workers._get_concurrency', mock.MagicMock(return_value=1))
    @mock.patch('pulp.server.async.manage_workers.os.path.exists',
                mock.MagicMock(return_value=True))
    @mock.patch('pulp.server.async.manage_workers.subprocess.Popen')
    @mock.patch('sys.stdout')
    def test_unit_path_does_exist_correctly(self, stdout, Popen):
        """
        Test the case for when the unit path does exist, and its contents are correct. It should
        start it, but should not write it again.
        """
        pipe_output = ('some output', None)
        Popen.return_value = mock.MagicMock()
        Popen.return_value.returncode = 0
        Popen.return_value.communicate.return_value = pipe_output
        expected_read_data = manage_workers._WORKER_TEMPLATE % {
            'num': 0, 'environment_file': manage_workers._ENVIRONMENT_FILE}

        with mock.patch('__builtin__.open', autospec=True) as mock_open:
            mock_file = mock.MagicMock(spec=file)
            mock_file.read.return_value = expected_read_data
            mock_context = mock.MagicMock()
            mock_context.__enter__.return_value = mock_file
            mock_open.return_value = mock_context
            manage_workers._start_workers()

        # Make sure open was called correctly
        unit_filename = manage_workers._UNIT_FILENAME_TEMPLATE % 0
        expected_path = os.path.join(manage_workers._SYSTEMD_UNIT_PATH, unit_filename)
        mock_open.assert_called_once_with(expected_path)
        file_context = mock_open()
        file_context.__enter__.assert_called_once_with()
        file_handle = file_context.__enter__()
        file_handle.read.assert_called_once_with()
        file_context.__exit__.assert_called_once_with(None, None, None)

        # Make sure we started the worker correctly
        Popen.assert_called_once_with('systemctl start %s' % unit_filename, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, shell=True)
        pipe = Popen()
        pipe.communicate.assert_called_once_with()

        # Make sure we printed the output of the pipe
        self.assertEqual(stdout.write.call_count, 2)
        self.assertEqual(stdout.write.mock_calls[0][1][0], pipe_output[0])
        self.assertEqual(stdout.write.mock_calls[1][1][0], '\n')

    @mock.patch('pulp.server.async.manage_workers._get_concurrency', mock.MagicMock(return_value=1))
    @mock.patch('pulp.server.async.manage_workers.os.path.exists',
                mock.MagicMock(return_value=True))
    @mock.patch('pulp.server.async.manage_workers.subprocess.Popen')
    @mock.patch('sys.stdout')
    def test_unit_path_does_exist_incorrectly(self, stdout, Popen):
        """
        Test the case for when the unit path does exist, but its contents are incorrect. It should
        write it and then start it.
        """
        pipe_output = ('some output', None)
        Popen.return_value = mock.MagicMock()
        Popen.return_value.returncode = 0
        Popen.return_value.communicate.return_value = pipe_output

        with mock.patch('__builtin__.open', autospec=True) as mock_open:
            mock_file = mock.MagicMock(spec=file)
            mock_file.read.return_value = 'This file has the wrong contents.'
            mock_context = mock.MagicMock()
            mock_context.__enter__.return_value = mock_file
            mock_open.return_value = mock_context
            # Set up the unit file to have the incorrect contents
            manage_workers._start_workers()

        # Make sure open was called correctly. It should be called twice, once for reading, and
        # again for writing
        unit_filename = manage_workers._UNIT_FILENAME_TEMPLATE % 0
        expected_path = os.path.join(manage_workers._SYSTEMD_UNIT_PATH, unit_filename)
        expected_file_contents = manage_workers._WORKER_TEMPLATE % {
            'num': 0, 'environment_file': manage_workers._ENVIRONMENT_FILE}
        self.assertEqual(mock_open.call_count, 2)
        # Let's inspect the read call
        first_open = mock_open.mock_calls[0]
        self.assertEqual(first_open[1], (expected_path,))
        file_context = first_open()
        file_context.__enter__.assert_called_once_with()
        file_handle = file_context.__enter__()
        file_handle.read.assert_called_once_with()
        file_context.__exit__.assert_called_once_with(None, None, None)
        # Now, let's inspect the write call
        second_open = mock_open.mock_calls[4]
        self.assertEqual(second_open[1], (expected_path, 'w'))
        file_context = second_open()
        file_context.__enter__.assert_called_once_with()
        file_handle = file_context.__enter__()
        file_handle.write.assert_called_once_with(expected_file_contents)
        file_context.__exit__.assert_called_once_with(None, None, None)

        # Make sure we started the worker correctly
        Popen.assert_called_once_with('systemctl start %s' % unit_filename, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, shell=True)
        pipe = Popen()
        pipe.communicate.assert_called_once_with()

        # Make sure we printed the output of the pipe
        self.assertEqual(stdout.write.call_count, 2)
        self.assertEqual(stdout.write.mock_calls[0][1][0], pipe_output[0])
        self.assertEqual(stdout.write.mock_calls[1][1][0], '\n')

    @mock.patch('pulp.server.async.manage_workers._get_concurrency', mock.MagicMock(return_value=1))
    # Setting this return value to False will simulate the file not existing
    @mock.patch('pulp.server.async.manage_workers.os.path.exists',
                mock.MagicMock(return_value=False))
    @mock.patch('pulp.server.async.manage_workers.subprocess.Popen')
    @mock.patch('sys.stdout')
    def test_unit_path_does_not_exist(self, stdout, Popen):
        """
        Test the case for when the unit path does not exist. It should write it and start it.
        """
        pipe_output = ('some output', None)
        Popen.return_value = mock.MagicMock()
        Popen.return_value.returncode = 0
        Popen.return_value.communicate.return_value = pipe_output

        with mock.patch('__builtin__.open', autospec=True) as mock_open:
            mock_file = mock.MagicMock(spec=file)
            mock_context = mock.MagicMock()
            mock_context.__enter__.return_value = mock_file
            mock_open.return_value = mock_context
            manage_workers._start_workers()

        # Make sure open was called correctly. It should be called once for writing
        unit_filename = manage_workers._UNIT_FILENAME_TEMPLATE % 0
        expected_path = os.path.join(manage_workers._SYSTEMD_UNIT_PATH, unit_filename)
        expected_file_contents = manage_workers._WORKER_TEMPLATE % {
            'num': 0, 'environment_file': manage_workers._ENVIRONMENT_FILE}
        # Now, let's inspect the write call
        mock_open.assert_called_once_with(expected_path, 'w')
        file_context = mock_open()
        file_context.__enter__.assert_called_once_with()
        file_handle = file_context.__enter__()
        file_handle.write.assert_called_once_with(expected_file_contents)
        file_context.__exit__.assert_called_once_with(None, None, None)

        # Make sure we started the worker correctly
        Popen.assert_called_once_with('systemctl start %s' % unit_filename, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, shell=True)
        pipe = Popen()
        pipe.communicate.assert_called_once_with()

        # Make sure we printed the output of the pipe
        self.assertEqual(stdout.write.call_count, 2)
        self.assertEqual(stdout.write.mock_calls[0][1][0], pipe_output[0])
        self.assertEqual(stdout.write.mock_calls[1][1][0], '\n')


class TestStopWorkers(unittest.TestCase):
    """
    Test the _stop_workers() function.
    """
    @mock.patch('pulp.server.async.manage_workers.glob')
    @mock.patch('pulp.server.async.manage_workers.subprocess.Popen')
    @mock.patch('sys.stdout')
    def test__stop_workers(self, stdout, Popen, glob):
        """
        Test _stop_workers() with one worker.
        """
        pipe_output = ('some output', None)
        Popen.return_value = mock.MagicMock()
        Popen.return_value.returncode = 0
        Popen.return_value.communicate.return_value = pipe_output
        unit_filename = manage_workers._UNIT_FILENAME_TEMPLATE % 0
        unit_path = os.path.join(manage_workers._SYSTEMD_UNIT_PATH, unit_filename)
        glob.return_value = (unit_path,)

        manage_workers._stop_workers()

        Popen.assert_called_once_with('systemctl stop %s' % unit_filename, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, shell=True)
        pipe = Popen()
        pipe.communicate.assert_called_once_with()

        # Make sure we printed the output of the pipe
        self.assertEqual(stdout.write.call_count, 2)
        self.assertEqual(stdout.write.mock_calls[0][1][0], pipe_output[0])
        self.assertEqual(stdout.write.mock_calls[1][1][0], '\n')

    @mock.patch('pulp.server.async.manage_workers.glob')
    @mock.patch('pulp.server.async.manage_workers.subprocess.Popen')
    @mock.patch('pulp.server.async.manage_workers.sys.exit')
    @mock.patch('sys.stderr')
    @mock.patch('sys.stdout')
    def test_systemctl_non_zero_exit_code(self, stdout, stderr, exit, Popen, glob):
        """
        _start_workers() uses systemctl. This test ensures that a non-zero exit code from systemctl
        is handled appropriately.
        """
        class SysExit(Exception):
            pass
        exit.side_effect = SysExit()
        pipe_output = ('some output', 'some errors')
        Popen.return_value = mock.MagicMock()
        Popen.return_value.returncode = 42
        Popen.return_value.communicate.return_value = pipe_output
        unit_filename = manage_workers._UNIT_FILENAME_TEMPLATE % 0
        unit_path = os.path.join(manage_workers._SYSTEMD_UNIT_PATH, unit_filename)
        glob.return_value = (unit_path,)

        self.assertRaises(SysExit, manage_workers._stop_workers)

        Popen.assert_called_once_with('systemctl stop %s' % unit_filename, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, shell=True)
        pipe = Popen()
        pipe.communicate.assert_called_once_with()

        # Make sure we printed the output of the pipe
        self.assertEqual(stdout.write.call_count, 2)
        self.assertEqual(stdout.write.mock_calls[0][1][0], pipe_output[0])
        self.assertEqual(stdout.write.mock_calls[1][1][0], '\n')
        # And the errors
        self.assertEqual(stderr.write.call_count, 1)
        self.assertEqual(stderr.write.mock_calls[0][1][0], pipe_output[1])
        # Make sure the exit code was passed on
        exit.assert_called_once_with(42)
