# -*- coding: utf-8 -*-
#
# Copyright © 2014 Red Hat, Inc.
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
This module contains tests for the pulp.server.logs module.
"""
from cStringIO import StringIO
import ConfigParser
import logging
import os
import sys
import traceback
import unittest
import Queue
import threading
import time

import mock

from pulp.server import logs


class TestBlacklistLoggers(unittest.TestCase):
    """
    Test the _blacklist_loggers() function.
    """
    @mock.patch('pulp.server.logs.LOG_BLACKLIST', ['logger_a', 'logger_b'])
    @mock.patch('pulp.server.logs.logging.getLogger')
    def test_blacklist_loggers(self, getLogger):
        """
        Ensure that _blacklist_loggers does the right thing for the given loggers.
        """
        # logger_c shouldn't get disabled
        loggers = {'logger_c': mock.MagicMock()}
        loggers['logger_c'].disabled = False
        loggers['logger_c'].propagate = True

        def _get_logger(logger_name):
            """
            Return logger_a or logger_b by logger-name.
            """
            if logger_name not in loggers:
                loggers[logger_name] = mock.MagicMock()
            return loggers[logger_name]
        getLogger.side_effect = _get_logger

        logs._blacklist_loggers()

        self.assertEqual(set(loggers.keys()), set(['logger_a', 'logger_b', 'logger_c']))
        for logger_name in ['logger_a', 'logger_b']:
            logger = loggers[logger_name]
            self.assertEqual(logger.disabled, True)
            self.assertEqual(logger.propagate, False)
        # logger_c should not have been blacklisted
        logger = loggers['logger_c']
        self.assertEqual(logger.disabled, False)
        self.assertEqual(logger.propagate, True)


class TestCompliantSysLogHandler(unittest.TestCase):
    """
    Test the CompliantSysLogHandler class.
    """
    def test__calculate_formatter_buffer(self):
        """
        Test that the formatter buffer calculates the correct difference in size between raw
        messages and formatted messages.
        """
        format_string = 'pulp: %(name)s:%(levelname)s: %(message)s'
        formatter = logging.Formatter(format_string)
        handler = logs.CompliantSysLogHandler('/dev/log',
                                              facility=logs.CompliantSysLogHandler.LOG_DAEMON)
        handler.setFormatter(formatter)
        log_message = 'Error, %s!'
        log_args = ('World',)
        record = logging.LogRecord(
            name='pulp.test.module', level=logging.ERROR, pathname='/some/path', lineno=527,
            msg=log_message, args=log_args, exc_info=None, func='some_function')

        formatter_buffer = handler._calculate_formatter_buffer(record)

        # The log message should be "Error, World!", which is 13 bytes. The formatted message
        # should be "pulp: pulp.test.module:ERROR: Error, World!", which is 43 bytes. Thus,
        # formatter_buffer should be 30.
        self.assertEqual(formatter_buffer, 30)

    def test__calculate_formatter_buffer_with_multibyte_characters(self):
        """
        Test that the formatter buffer calculates the correct difference in size between raw
        messages and formatted messages when multibyte characters are involved.
        """
        # This format string contains a three byte character
        format_string = u'☃: %(name)s:%(levelname)s: %(message)s'
        formatter = logging.Formatter(format_string)
        handler = logs.CompliantSysLogHandler('/dev/log',
                                              facility=logs.CompliantSysLogHandler.LOG_DAEMON)
        handler.setFormatter(formatter)
        log_message = 'Here is a two-byte character: %s'
        log_args = (u'ԃ',)
        record = logging.LogRecord(
            name='pulp.test.module', level=logging.INFO, pathname='/some/path', lineno=527,
            msg=log_message, args=log_args, exc_info=None, func='some_function')

        formatter_buffer = handler._calculate_formatter_buffer(record)

        # The log message should be "Here is a two-byte character: ԃ", which is 31 characters, but
        # 32 bytes (since one is two bytes). The formatted message
        # should be "☃: pulp.test.module:INFO: Here is a two-byte character: ԃ", which is 57
        # characters, and 60 bytes. Thus, formatter_buffer should be 28. If it went only by
        # number of characters, it would mistakenly return 26.
        self.assertEqual(formatter_buffer, 28)

    def test__cut_message_handles_multibyte_characters(self):
        """
        Make sure that _cut_messages() will not cut multi-byte characters in half. We'll use a
        unicode snowman, both because it is a three byte character and because it is fun. We'll try
        to cut the string on all four boundaries around the three bytes and make sure the snowman
        lives through every cut. Note that all three bytes of the snowman must always be entirely
        in one string in all of our assertions.
        """
        msg = u'Please do not cut ☃ in half.'

        with mock.patch('pulp.server.logs.CompliantSysLogHandler._log_id') as _log_id:
            _log_id.return_value = "PID-TID-"

            # This one cuts exactly before the snowman starts, so it's OK.
            with mock.patch('pulp.server.logs.CompliantSysLogHandler.MAX_MSG_LENGTH', 26):
                messages = list(logs.CompliantSysLogHandler._cut_message(msg, 0, ""))

                expected_messages = ['PID-TID-Please do not cut ', 'PID-TID-\xe2\x98\x83 in half.']
                self.assertEqual(messages, expected_messages)

            # 27 bytes would allow \xe2 in the first string, but we don't want to kill the snowman
            with mock.patch('pulp.server.logs.CompliantSysLogHandler.MAX_MSG_LENGTH', 27):
                messages = list(logs.CompliantSysLogHandler._cut_message(msg, 0, ""))

                expected_messages = ['PID-TID-Please do not cut ', 'PID-TID-\xe2\x98\x83 in half.']
                self.assertEqual(messages, expected_messages)

            # 28 bytes would allow \xe2\x98 in the first string, but we don't want to kill the snowman
            with mock.patch('pulp.server.logs.CompliantSysLogHandler.MAX_MSG_LENGTH', 28):
                messages = list(logs.CompliantSysLogHandler._cut_message(msg, 0, ""))

                expected_messages = ['PID-TID-Please do not cut ', 'PID-TID-\xe2\x98\x83 in half.']
                self.assertEqual(messages, expected_messages)

            # This one is exactly long enough to include the snowman in the first cut
            with mock.patch('pulp.server.logs.CompliantSysLogHandler.MAX_MSG_LENGTH', 29):
                messages = list(logs.CompliantSysLogHandler._cut_message(msg, 0, ""))

                expected_messages = ['PID-TID-Please do not cut \xe2\x98\x83', 'PID-TID- in half.']
                self.assertEqual(messages, expected_messages)

    def test__cut_message_handles_multibyte_characters_at_end(self):
        """
        Make sure that _cut_messages() will not blow up if a message ends with a multi-byte
        character exactly at the allowed length. We'll use a unicode snowman, both because it is a
        three byte character and because it is fun.
        """
        msg = u'Please do not kill ☃'

        # This one cuts exactly after the snowman, so it's OK.
        with mock.patch('pulp.server.logs.CompliantSysLogHandler.MAX_MSG_LENGTH', 22):
            messages = list(logs.CompliantSysLogHandler._cut_message(msg, 0, ""))

            expected_messages = ['Please do not kill \xe2\x98\x83']
            self.assertEqual(messages, expected_messages)

    @mock.patch('pulp.server.logs.CompliantSysLogHandler.MAX_MSG_LENGTH', 48)
    def test__cut_message_with_buffer(self):
        """
        Make sure the case where the message is an empty string is handled well.
        """
        long_string = 'This string is too long with the formatter.'

        with mock.patch('pulp.server.logs.CompliantSysLogHandler._log_id') as _log_id:
            _log_id.return_value = "PID-TID-"

            # Let's suppose that we have a 6 character formatter of "pulp: %(message)s"
            messages = list(logs.CompliantSysLogHandler._cut_message(long_string, 6, ""))

            expected_messages = ['PID-TID-This string is too long with the f', 'PID-TID-ormatter.']
            self.assertEqual(messages, expected_messages)
            # With 6 characters added by the formatter, we can only have 42 characters in the string
            # now. Obviously this check is redundant given the one above, but it's easier for a human
            # to know that 42 is the right answer, because it is the meaning of life.
            self.assertEqual(len(expected_messages[0]), 42)

    def test__cut_message_with_empty_string(self):
        """
        Make sure the case where the message is an empty string is handled well.
        """

        messages = list(logs.CompliantSysLogHandler._cut_message('', 0, ''))

        self.assertEqual(messages, [''])

    @mock.patch('pulp.server.logs.CompliantSysLogHandler.MAX_MSG_LENGTH', 9)
    def test__cut_message_with_long_message(self):
        """
        Make sure the case where a message needs cutting is handled well.
        """
        msg = "This message needs cutting, because it's longer than 9 characters."

        with mock.patch('pulp.server.logs.CompliantSysLogHandler._log_id') as _log_id:
            _log_id.return_value = "PID-"

            messages = list(logs.CompliantSysLogHandler._cut_message(msg, 0, ""))

            expected_messages = ['PID-This ', 'PID-messa', 'PID-ge ne', 'PID-eds c', 'PID-uttin',
                                 'PID-g, be', 'PID-cause', "PID- it's", 'PID- long', 'PID-er th',
                                 'PID-an 9 ', 'PID-chara', 'PID-cters', 'PID-.']
            self.assertEqual(messages, expected_messages)

    def test__cut_message_with_short_message(self):
        """
        Make sure the case where a message doesn't need cutting is handled well.
        """
        msg = "No cutting necessary."

        messages = list(logs.CompliantSysLogHandler._cut_message(msg, 0, ""))

        expected_messages = ['No cutting necessary.']
        self.assertEqual(messages, expected_messages)

    @mock.patch('pulp.server.logs.CompliantSysLogHandler.MAX_MSG_LENGTH', 43)
    def test__cut_message_overflows_when_prepended(self):
        """
        Make sure that when the last line length is close to the limit and a PID
        is prepended that the resultant line does not go over the limit.
        """
        msg = "The first line ends right on the limit and second line only overflows if prepended"

        with mock.patch('pulp.server.logs.CompliantSysLogHandler._log_id') as _log_id:
            _log_id.return_value = "PID-"

            messages = list(logs.CompliantSysLogHandler._cut_message(msg, 0, ""))

            expected_messages = ["PID-The first line ends right on the limit ",
                                 "PID-and second line only overflows if prepe", "PID-nded"]
            self.assertEqual(messages, expected_messages)

    @mock.patch('pulp.server.logs.logging.handlers.SysLogHandler.emit')
    def test_emit_with_compliant_message(self, super_emit):
        """
        Test emit() with an already compliant message.
        """
        format_string = 'pulp: %(name)s:%(levelname)s: %(message)s'
        formatter = logging.Formatter(format_string)
        handler = logs.CompliantSysLogHandler('/dev/log',
                                              facility=logs.CompliantSysLogHandler.LOG_DAEMON)
        handler.setFormatter(formatter)
        log_message = 'This %(message)s is just fine.'
        log_args = ({'message': 'message'},)
        record = logging.LogRecord(
            name='pulp.test.module', level=logging.INFO, pathname='/some/path', lineno=527,
            msg=log_message, args=log_args, exc_info=None, func='some_function')

        handler.emit(record)

        self.assertEqual(super_emit.call_count, 1)
        new_record = super_emit.mock_calls[0][1][1]
        self.assertEqual(new_record.name, 'pulp.test.module')
        self.assertEqual(new_record.levelno, logging.INFO)
        self.assertEqual(new_record.pathname, '/some/path')
        self.assertEqual(new_record.lineno, 527)
        # Note that the new record has already performed the string substitution, so msg is
        # complete and args is now the empty tuple.
        self.assertEqual(new_record.msg, 'This message is just fine.')
        self.assertEqual(new_record.args, tuple())
        self.assertEqual(new_record.exc_info, None)
        self.assertEqual(new_record.funcName, 'some_function')

    @mock.patch('pulp.server.logs.CompliantSysLogHandler.MAX_MSG_LENGTH', 54)
    @mock.patch('pulp.server.logs.logging.handlers.SysLogHandler.emit')
    def test_emit_with_long_lines(self, super_emit):
        """
        Test emit() with a message that contains long lines. Make sure the formatter is accounted
        for in the long line lengths by setting the MAX_MSG_LENGTH to 54, which is exactly one byte
        too short to accomodate for the length of the message given the format string.
        """
        # This format string will add 29 characters to each message, which will push our message
        # over the limit by one character.
        with mock.patch('pulp.server.logs.CompliantSysLogHandler._log_id') as _log_id:
            _log_id.return_value = "PID-"

            format_string = 'pulp: %(name)s:%(levelname)s: %(message)s'
            formatter = logging.Formatter(format_string)
            handler = logs.CompliantSysLogHandler('/dev/log',
                                                  facility=logs.CompliantSysLogHandler.LOG_DAEMON)
            handler.setFormatter(formatter)
            # This message is 26 bytes, which will exceed the allowed length by one byte when combined
            # with our format string. It will have to be split into two messages.
            log_message = 'This %(message)s is very long.'
            log_args = ({'message': 'message'},)
            record = logging.LogRecord(
                name='pulp.test.module', level=logging.INFO, pathname='/some/path', lineno=527,
                msg=log_message, args=log_args, exc_info=None, func='some_function')

            handler.emit(record)

            self.assertEqual(super_emit.call_count, 2)
            # Let's make sure each new record has the right non-message attributes
            for mock_call in super_emit.mock_calls:
                new_record = mock_call[1][1]
                self.assertEqual(new_record.name, 'pulp.test.module')
                self.assertEqual(new_record.levelno, logging.INFO)
                self.assertEqual(new_record.pathname, '/some/path')
                self.assertEqual(new_record.lineno, 527)
                self.assertEqual(new_record.args, tuple())
                self.assertEqual(new_record.exc_info, None)
                self.assertEqual(new_record.funcName, 'some_function')
            # Now let's make sure the messages were split correctly. They will not be formatted yet,
            # but they should have left exactly enough room for formatting.
            expected_messages = ['PID-This message is very ', 'PID-long.']
            messages = [mock_call[1][1].msg for mock_call in super_emit.mock_calls]
            self.assertEqual(messages, expected_messages)

    @mock.patch('pulp.server.logs.CompliantSysLogHandler.MAX_MSG_LENGTH', 60)
    @mock.patch('pulp.server.logs.logging.handlers.SysLogHandler.emit')
    def test_emit_prepends_pid_if_newlines(self, super_emit):
        """Test emit() with a message that contains newlines."""

        with mock.patch('pulp.server.logs.CompliantSysLogHandler._log_id') as _log_id:
            _log_id.return_value = "PID-TID-"

            format_string = 'pulp: %(name)s:%(levelname)s: %(message)s'
            formatter = logging.Formatter(format_string)
            handler = logs.CompliantSysLogHandler('/dev/log',
                                                  facility=logs.CompliantSysLogHandler.LOG_DAEMON)
            handler.setFormatter(formatter)
            log_message = 'This %(message)s has a \nnewline.'
            log_args = ({'message': 'message'},)
            record = logging.LogRecord(
                name='pulp.test.module', level=logging.INFO, pathname='/some/path', lineno=527,
                msg=log_message, args=log_args, exc_info=None, func='some_function')
            handler.emit(record)
            messages = [mock_call[1][1].msg for mock_call in super_emit.mock_calls]
            expected_messages = ['PID-TID-This message has a ', 'PID-TID-newline.']
            self.assertEqual(expected_messages, messages)

    @mock.patch('pulp.server.logs.CompliantSysLogHandler.MAX_MSG_LENGTH', 62)
    @mock.patch('pulp.server.logs.logging.handlers.SysLogHandler.emit')
    def test_emit_prepends_pid_if_too_long(self, super_emit):
        """Test emit() with a message that is longer than the maximum allowable length."""

        with mock.patch('pulp.server.logs.CompliantSysLogHandler._log_id') as _log_id:
            _log_id.return_value = "PID-TID-"

            format_string = 'pulp: %(name)s:%(levelname)s: %(message)s'
            formatter = logging.Formatter(format_string)
            handler = logs.CompliantSysLogHandler('/dev/log',
                                                  facility=logs.CompliantSysLogHandler.LOG_DAEMON)
            handler.setFormatter(formatter)
            log_message = 'This %(message)s is too long for a single line.'
            log_args = ({'message': 'message'},)
            record = logging.LogRecord(
                name='pulp.test.module', level=logging.INFO, pathname='/some/path', lineno=527,
                msg=log_message, args=log_args, exc_info=None, func='some_function')
            handler.emit(record)
            messages = [mock_call[1][1].msg for mock_call in super_emit.mock_calls]
            expected_messages = ['PID-TID-This message is too long ', 'PID-TID-for a single line.']
            self.assertEqual(expected_messages, messages)

    @mock.patch('pulp.server.logs.CompliantSysLogHandler.MAX_MSG_LENGTH', 74)
    @mock.patch('pulp.server.logs.logging.handlers.SysLogHandler.emit')
    def test_emit_does_not_prepend_pid_if_short_line_without_newlines(self, super_emit):
        """Test that message id is not prepended if the message is already within guidlines."""
        format_string = 'pulp: %(name)s:%(levelname)s: %(message)s'
        formatter = logging.Formatter(format_string)
        handler = logs.CompliantSysLogHandler('/dev/log',
                                              facility=logs.CompliantSysLogHandler.LOG_DAEMON)
        handler.setFormatter(formatter)
        log_message = 'This %(message)s is short and has no newline.'
        log_args = ({'message': 'message'},)
        record = logging.LogRecord(
            name='pulp.test.module', level=logging.INFO, pathname='/some/path', lineno=527,
            msg=log_message, args=log_args, exc_info=None, func='some_function')
        handler.emit(record)
        messages = [mock_call[1][1].msg for mock_call in super_emit.mock_calls]
        expected_messages = ['This message is short and has no newline.']
        self.assertEqual(expected_messages, messages)

    @mock.patch('pulp.server.logs.CompliantSysLogHandler.MAX_MSG_LENGTH', 53)
    @mock.patch('pulp.server.logs.logging.handlers.SysLogHandler.emit')
    def test_emit_does_not_prepend_pid_twice(self, super_emit):
        """
        Make sure that if there are newline characers and the message is too long
        the msg_id is not prepended twice.
        """
        with mock.patch('pulp.server.logs.CompliantSysLogHandler._log_id') as _log_id:
            _log_id.return_value = "PID-"

            format_string = 'pulp: %(name)s:%(levelname)s: %(message)s'
            formatter = logging.Formatter(format_string)
            handler = logs.CompliantSysLogHandler('/dev/log',
                                                  facility=logs.CompliantSysLogHandler.LOG_DAEMON)
            handler.setFormatter(formatter)
            log_message = 'This %(message)s has a \nnewline and is too long.'
            log_args = ({'message': 'message'},)
            record = logging.LogRecord(
                name='pulp.test.module', level=logging.INFO, pathname='/some/path', lineno=527,
                msg=log_message, args=log_args, exc_info=None, func='some_function')
            handler.emit(record)
            messages = [mock_call[1][1].msg for mock_call in super_emit.mock_calls]
            expected_messages = ['PID-This message has a ', 'PID-newline and is too l', 'PID-ong.']
            self.assertEqual(expected_messages, messages)

    @mock.patch('pulp.server.logs.CompliantSysLogHandler.MAX_MSG_LENGTH', 58)
    @mock.patch('pulp.server.logs.logging.handlers.SysLogHandler.emit')
    def test_emit_with_long_lines_and_newlines(self, super_emit):
        """
        Test emit() with a message that contains long lines and newlines.
        """
        # This format string will add 29 characters to each message, which will push our message
        # over the limit by one character.
        with mock.patch('pulp.server.logs.CompliantSysLogHandler._log_id') as _log_id:
            _log_id.return_value = "PID-"

            format_string = 'pulp: %(name)s:%(levelname)s: %(message)s'
            formatter = logging.Formatter(format_string)
            handler = logs.CompliantSysLogHandler('/dev/log',
                                                  facility=logs.CompliantSysLogHandler.LOG_DAEMON)
            handler.setFormatter(formatter)
            # This message is 26 bytes before the newline, which will exceed the allowed length by one
            # byte when combined with our format string. The newline will cause another split after the
            # period. This message will have to be split into three messages.
            log_message = 'This %(message)s is very long.\nAnd it has a newline.'
            log_args = ({'message': 'message'},)
            record = logging.LogRecord(
                name='pulp.test.module', level=logging.INFO, pathname='/some/path', lineno=527,
                msg=log_message, args=log_args, exc_info=None, func='some_function')

            handler.emit(record)

            self.assertEqual(super_emit.call_count, 3)
            # Let's make sure each new record has the right non-message attributes
            for mock_call in super_emit.mock_calls:
                new_record = mock_call[1][1]
                self.assertEqual(new_record.name, 'pulp.test.module')
                self.assertEqual(new_record.levelno, logging.INFO)
                self.assertEqual(new_record.pathname, '/some/path')
                self.assertEqual(new_record.lineno, 527)
                self.assertEqual(new_record.args, tuple())
                self.assertEqual(new_record.exc_info, None)
                self.assertEqual(new_record.funcName, 'some_function')
            # Now let's make sure the messages were split correctly. They will not be formatted yet,
            # but the first should have left exactly enough room for formatting, and the newline should
            # have caused a third message.
            expected_messages = ['PID-This message is very long', 'PID-.', 'PID-And it has a newline.']
            messages = [mock_call[1][1].msg for mock_call in super_emit.mock_calls]
            self.assertEqual(messages, expected_messages)

    @mock.patch('pulp.server.logs.logging.handlers.SysLogHandler.emit')
    def test_emit_with_newlines(self, super_emit):
        """
        Test emit() with a message that contains newlines.
        """
        with mock.patch('pulp.server.logs.CompliantSysLogHandler._log_id') as _log_id:
            _log_id.return_value = "PID-"

            format_string = 'pulp: %(name)s:%(levelname)s: %(message)s'
            formatter = logging.Formatter(format_string)
            handler = logs.CompliantSysLogHandler('/dev/log',
                                                  facility=logs.CompliantSysLogHandler.LOG_DAEMON)
            handler.setFormatter(formatter)
            # This message is not too long,  but the newline should cause a split.
            log_message = 'This %(newline)s should be OK.'
            log_args = ({'newline': '\n'},)
            record = logging.LogRecord(
                name='pulp.test.module', level=logging.INFO, pathname='/some/path', lineno=527,
                msg=log_message, args=log_args, exc_info=None, func='some_function')

            handler.emit(record)

            self.assertEqual(super_emit.call_count, 2)
            # Let's make sure each new record has the right non-message attributes
            for mock_call in super_emit.mock_calls:
                new_record = mock_call[1][1]
                self.assertEqual(new_record.name, 'pulp.test.module')
                self.assertEqual(new_record.levelno, logging.INFO)
                self.assertEqual(new_record.pathname, '/some/path')
                self.assertEqual(new_record.lineno, 527)
                self.assertEqual(new_record.args, tuple())
                self.assertEqual(new_record.exc_info, None)
                self.assertEqual(new_record.funcName, 'some_function')
            # Let's make sure the split around the newline happened correctly.
            expected_messages = ['PID-This ', 'PID- should be OK.']
            messages = [mock_call[1][1].msg for mock_call in super_emit.mock_calls]
            self.assertEqual(messages, expected_messages)

    @mock.patch('pulp.server.logs.logging.handlers.SysLogHandler.emit')
    def test_emit_with_traceback(self, super_emit):
        """
        Make sure emit() handles tracebacks appropriately.
        """
        with mock.patch('pulp.server.logs.CompliantSysLogHandler._log_id') as _log_id:
            _log_id.return_value = "PID-"

            format_string = 'pulp: %(name)s:%(levelname)s: %(message)s'
            formatter = logging.Formatter(format_string)
            handler = logs.CompliantSysLogHandler('/dev/log',
                                                  facility=logs.CompliantSysLogHandler.LOG_DAEMON)
            handler.setFormatter(formatter)
            try:
                pid = 1234
                raise Exception('This is terrible. %d killed' % pid)
            except:
                exc_info = sys.exc_info()
            task_id = 5678
            log_message = 'Uh oh.  task [%d] failed'
            log_args = (task_id,)
            record = logging.LogRecord(
                name='pulp.test.module', level=logging.ERROR, pathname='/some/path', lineno=527,
                msg=log_message, args=log_args, exc_info=exc_info, func='some_function')

            handler.emit(record)

            # 5 records should be emitted. One for the message, and the traceback is 4 lines.
            self.assertEqual(super_emit.call_count, 5)
            # Let's make sure each new record has the right non-message attributes
            for mock_call in super_emit.mock_calls:
                new_record = mock_call[1][1]
                self.assertEqual(new_record.name, 'pulp.test.module')
                self.assertEqual(new_record.levelno, logging.ERROR)
                self.assertEqual(new_record.pathname, '/some/path')
                self.assertEqual(new_record.lineno, 527)
                self.assertEqual(new_record.args, tuple())
                self.assertEqual(new_record.exc_info, None)
                self.assertEqual(new_record.funcName, 'some_function')
            # Let's make sure the split around the newline happened correctly.
            strio = StringIO()
            traceback.print_exception(exc_info[0], exc_info[1], exc_info[2], None, strio)
            strio.seek(0)
            traceback_lines = strio.read().split('\n')
            # The last element of traceback lines is an empty string that won't be printed, so let's
            # pop it off
            traceback_lines.pop()
            expected_messages = [log_message % task_id]
            expected_messages.extend(traceback_lines)
            expected_messages = ["PID-" + msg for msg in expected_messages]

            messages = [mock_call[1][1].msg for mock_call in super_emit.mock_calls]
            self.assertEqual(messages, expected_messages)

    @mock.patch('pulp.server.logs.logging.handlers.SysLogHandler.emit')
    def test_emit_with_traceback_and_non_string_message(self, super_emit):
        """
        Make sure emit() handles tracebacks appropriately.
        """
        with mock.patch('pulp.server.logs.CompliantSysLogHandler._log_id') as _log_id:
            _log_id.return_value = "PID-"

            format_string = 'pulp: %(name)s:%(levelname)s: %(message)s'
            formatter = logging.Formatter(format_string)
            handler = logs.CompliantSysLogHandler('/dev/log',
                                                  facility=logs.CompliantSysLogHandler.LOG_DAEMON)
            handler.setFormatter(formatter)
            try:
                raise Exception('This is terrible.')
            except:
                exc_info = sys.exc_info()
            # Sadly, all over our code we log non-string objects. This is bad, but we don't have time
            # to fix it right now, so we need to make sure our emitter handles this case.
            log_message = 42
            log_args = tuple()
            record = logging.LogRecord(
                name='pulp.test.module', level=logging.ERROR, pathname='/some/path', lineno=527,
                msg=log_message, args=log_args, exc_info=exc_info, func='some_function')

            handler.emit(record)

            # 5 records should be emitted. One for the message, and the traceback is 4 lines.
            self.assertEqual(super_emit.call_count, 5)
            # Let's make sure each new record has the right non-message attributes
            for mock_call in super_emit.mock_calls:
                new_record = mock_call[1][1]
                self.assertEqual(new_record.name, 'pulp.test.module')
                self.assertEqual(new_record.levelno, logging.ERROR)
                self.assertEqual(new_record.pathname, '/some/path')
                self.assertEqual(new_record.lineno, 527)
                self.assertEqual(new_record.args, tuple())
                self.assertEqual(new_record.exc_info, None)
                self.assertEqual(new_record.funcName, 'some_function')
            # Let's make sure the split around the newline happened correctly.
            strio = StringIO()
            traceback.print_exception(exc_info[0], exc_info[1], exc_info[2], None, strio)
            strio.seek(0)
            traceback_lines = strio.read().split('\n')
            # The last element of traceback lines is an empty string that won't be printed, so let's
            # pop it off
            traceback_lines.pop()
            expected_messages = ['42']
            expected_messages.extend(traceback_lines)
            expected_messages = ["PID-" + msg for msg in expected_messages]
            messages = [mock_call[1][1].msg for mock_call in super_emit.mock_calls]
            self.assertEqual(messages, expected_messages)

    @mock.patch('pulp.server.logs.CompliantSysLogHandler.MAX_MSG_LENGTH', 54)
    @mock.patch('pulp.server.logs.logging.handlers.SysLogHandler.emit')
    def test_emit_with_multiple_threads(self, super_emit):
        """
        Test that when multithreading, lines within the same thread contain the
        same thread id. Do this by splitting a thread and ensuring that all
        messages that share a message number have the same msg id prepended to it.
        """

        def log_message(q, num):
            """
            Log a message in two parts. Wait between so that other threads have
            a chance to get started this thread is finished.
            """
            wait = 0.001

            format_string = 'pulp: %(name)s:%(levelname)s: %(message)s'
            formatter = logging.Formatter(format_string)
            handler = logs.CompliantSysLogHandler('/dev/log',
                                                  facility=logs.CompliantSysLogHandler.LOG_DAEMON)
            handler.setFormatter(formatter)

            # Create and emit the first message of a thread
            log_message = '%(number)s this message is too long.'
            log_args = ({'number': str(num)},)
            record = logging.LogRecord(
                name='pulp.test.module', level=logging.INFO, pathname='/some/path', lineno=527,
                msg=log_message, args=log_args, exc_info=None, func='some_function')
            q.put(handler.emit(record))

            # Wait to ensure that this thread doesn't finish before the other
            # theads can be created.
            time.sleep(wait)

            # Log a second message using the same thread
            log_message = '%(number)s  This is the same thread.'
            log_args = ({'number': str(num)},)
            record = logging.LogRecord(
                name='pulp.test.module', level=logging.INFO, pathname='/some/path', lineno=527,
                msg=log_message, args=log_args, exc_info=None, func='some_function')
            q.put(handler.emit(record))

        # Start 10 seperate and identifiable logging threads
        q = Queue.Queue()
        msg_number = [i for i in range(10)]
        for num in msg_number:
            t = threading.Thread(target=log_message, args=(q, num))
            t.daemon = True
            t.start()

        # Wait to ensure that all threads finish
        time.sleep(0.1)
        messages = [mock_call[1][1].msg for mock_call in super_emit.mock_calls]

        # Create a dict that stores msg_number: msg_id and ensure that all
        # threads with the same msg_number share a msg_id. After complete, there
        # should be 10 items in the dictionary and each one should have been
        # checked against once.
        msg_id_dict = {}
        # not a constant because PID is variable length
        prepend_length = len(logs.CompliantSysLogHandler._log_id())
        check_same = 0
        for msg in messages:
            # The first character of the first line of a message after the
            # prepended id is an integer that shows which thread split this
            # message is a part of.
            if msg[prepend_length].isdigit() and msg_id_dict.get(msg[prepend_length]):
                check_same += 1
                self.assertTrue(msg_id_dict[msg[prepend_length]] == msg[:prepend_length])
            else:
                msg_id_dict[msg[prepend_length]] = msg[:prepend_length]

        # Ensure that dictionary was filled and each was checked
        self.assertTrue(check_same == 10)

class TestStartLogging(unittest.TestCase):
    """
    Test the configure_pulp_logging() function.
    """
    @mock.patch('pulp.server.logs._blacklist_loggers')
    @mock.patch('pulp.server.logs.config.config.get', return_value='WARNING')
    @mock.patch('pulp.server.logs.logging.getLogger')
    def test_calls__blacklist_loggers(self, getLogger, get, _blacklist_loggers):
        """
        Ensure that start_logging() calls _blacklist_loggers().
        """
        logs.start_logging()

        _blacklist_loggers.assert_called_once_with()

    @mock.patch('pulp.server.logs.logging')
    def test_calls__captureWarnings(self, _logging):
        """
        Ensure that start_logging() calls captureWarnings().
        """
        logs.start_logging()

        _logging.captureWarnings.assert_called_once_with(True)

    @mock.patch('pulp.server.logs.logging')
    def test_calls__captureWarnings_with_attribute_error(self, _logging):
        """
        Ensure that start_logging() calls captureWarnings() and handles AttributeError
        The validation for this is that the AttributeError is swallowed.
        """
        _logging.captureWarnings.side_effect = AttributeError

        logs.start_logging()

        _logging.captureWarnings.assert_called_once_with(True)

    @mock.patch('pulp.server.logs.config.config.get', return_value='something wrong')
    @mock.patch('pulp.server.logs.logging.getLogger')
    def test_log_level_invalid(self, getLogger, get):
        """
        Test that we still default to INFO if the user sets some non-existing log level.
        """
        root_logger = mock.MagicMock(spec=logging.Logger)
        root_logger.manager = mock.MagicMock()
        root_logger.manager.loggerDict = {}

        def fake_getLogger(name=None):
            if name is None:
                return root_logger
            root_logger.manager.loggerDict[name] = mock.MagicMock()
            return root_logger.manager.loggerDict[name]
        getLogger.side_effect = fake_getLogger

        logs.start_logging()

        # The config should have been queried for log level
        get.assert_called_once_with('server', 'log_level')
        # We should have defaulted
        root_logger.setLevel.assert_called_once_with(logging.INFO)

    @mock.patch('pulp.server.logs.config.config.get', return_value='error')
    @mock.patch('pulp.server.logs.logging.getLogger')
    def test_log_level_set(self, getLogger, get):
        """
        Test that we correctly allow users to set their log level.
        """
        root_logger = mock.MagicMock(spec=logging.Logger)
        root_logger.manager = mock.MagicMock()
        root_logger.manager.loggerDict = {}

        def fake_getLogger(name=None):
            if name is None:
                return root_logger
            root_logger.manager.loggerDict[name] = mock.MagicMock()
            return root_logger.manager.loggerDict[name]
        getLogger.side_effect = fake_getLogger

        logs.start_logging()

        # The config should have been queried for log level
        get.assert_called_once_with('server', 'log_level')
        # We should have used the user's setting
        root_logger.setLevel.assert_called_once_with(logging.ERROR)

    @mock.patch('pulp.server.logs.config.config.get',
                side_effect=ConfigParser.NoOptionError('server', 'log_level'))
    @mock.patch('pulp.server.logs.logging.getLogger')
    def test_log_level_unset(self, getLogger, get):
        """
        Test that we still default to INFO if the user doesn't set it.
        """
        root_logger = mock.MagicMock(spec=logging.Logger)
        root_logger.manager = mock.MagicMock()
        root_logger.manager.loggerDict = {}

        def fake_getLogger(name=None):
            if name is None:
                return root_logger
            if name not in root_logger.manager.loggerDict:
                root_logger.manager.loggerDict[name] = mock.MagicMock()
            return root_logger.manager.loggerDict[name]
        getLogger.side_effect = fake_getLogger

        logs.start_logging()

        # The config should have been queried for log level
        get.assert_called_once_with('server', 'log_level')
        # We should have defaulted
        root_logger.setLevel.assert_called_once_with(logs.DEFAULT_LOG_LEVEL)

    @mock.patch('pulp.server.logs.config.config.get', return_value='Debug')
    @mock.patch('pulp.server.logs.logging.getLogger')
    def test_root_logger_configured(self, getLogger, get):
        """
        This test ensures that the root logger is configured appropriately.
        """
        root_logger = mock.MagicMock(spec=logging.Logger)
        root_logger.manager = mock.MagicMock()
        root_logger.manager.loggerDict = {}

        def fake_getLogger(name=None):
            if name is None:
                return root_logger
            if name not in root_logger.manager.loggerDict:
                root_logger.manager.loggerDict[name] = mock.MagicMock()
            return root_logger.manager.loggerDict[name]
        getLogger.side_effect = fake_getLogger

        logs.start_logging()

        # Let's make sure the handler is setup right
        self.assertEqual(root_logger.addHandler.call_count, 1)
        root_handler = root_logger.addHandler.mock_calls[0][1][0]
        self.assertTrue(isinstance(root_handler, logs.CompliantSysLogHandler))
        self.assertEqual(root_handler.address, os.path.join('/', 'dev', 'log'))
        self.assertEqual(root_handler.facility, logs.CompliantSysLogHandler.LOG_DAEMON)

        # And the handler should have the formatter with our format string
        self.assertEqual(root_handler.formatter._fmt, logs.LOG_FORMAT_STRING)


class TestStopLogging(unittest.TestCase):
    """
    Test the stop_logging() function.
    """
    @mock.patch('pulp.server.logs.logging.shutdown')
    def test_stop_logging(self, shutdown):
        """
        Make sure that stop_logging() calls logging.shutdown().
        """
        logs.stop_logging()

        shutdown.assert_called_once_with()
