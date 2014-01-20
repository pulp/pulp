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
        mock_open = mock.mock_open(read_data=file_contents)

        with mock.patch('__builtin__.open', mock_open):
            contents = manage_workers._get_file_contents('/some/path')

        self.assertEqual(contents, file_contents)
        mock_open.assert_called_once_with('/some/path')
        # Make sure the file handle was treated properly
        file_handle = mock_open()
        file_handle.__enter__.assert_called_once_with()
        file_handle.read.assert_called_once_with()
        file_handle.__exit__.assert_called_once_with(None, None, None)


class TestStartWorkers(unittest.TestCase):
    """
    Test the _start_workers() function. For simplicity, these tests all set concurrency to 1.
    """
    @mock.patch('pulp.server.async.manage_workers._get_concurrency', mock.MagicMock(return_value=1))
    @mock.patch('pulp.server.async.manage_workers.subprocess.Popen')
    @mock.patch('sys.stdout')
    def test_unit_path_does_exist_correctly(self, stdout, Popen):
        """
        Test the case for when the unit path does exist, and its contents are correct. It should
        start it, but should not write it again.
        """
        pipe_output = ('some output',)
        Popen.return_value = mock.MagicMock()
        Popen.return_value.communicate.return_value = pipe_output
        expected_read_data = manage_workers._WORKER_TEMPLATE % {
            'num': 0, 'environment_file': manage_workers._ENVIRONMENT_FILE}
        mock_open = mock.mock_open(read_data=expected_read_data)

        with mock.patch('__builtin__.open', mock_open):
            manage_workers._start_workers()

        # Make sure open was called correctly
        unit_filename = manage_workers._UNIT_FILENAME_TEMPLATE % 0
        expected_path = os.path.join(manage_workers._SYSTEMD_UNIT_PATH, unit_filename)
        mock_open.assert_called_once_with(expected_path)
        file_handle = mock_open()
        file_handle.__enter__.assert_called_once_with()
        file_handle.read.assert_called_once_with()
        file_handle.__exit__.assert_called_once_with(None, None, None)

        # Make sure we started the worker correctly
        Popen.assert_called_once_with('systemctl start %s' % unit_filename, stdout=subprocess.PIPE,
                                      shell=True)
        pipe = Popen()
        pipe.communicate.assert_called_once_with()

        # Make sure we printed the output of the pipe
        self.assertEqual(stdout.write.call_count, 2)
        self.assertEqual(stdout.write.mock_calls[0][1][0], pipe_output[0])
        self.assertEqual(stdout.write.mock_calls[1][1][0], '\n')

    @mock.patch('pulp.server.async.manage_workers._get_concurrency', mock.MagicMock(return_value=1))
    def test_unit_path_does_exist_incorrectly(self):
        """
        Test the case for when the unit path does exist, but its contents are incorrect. It should
        write it and then start it.
        """
        self.fail()

    @mock.patch('pulp.server.async.manage_workers._get_concurrency', mock.MagicMock(return_value=1))
    def test_unit_path_does_not_exist(self):
        """
        Test the case for when the unit path does not exist. It should write it and start it.
        """
        self.fail()
