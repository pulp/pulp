"""
This module defines and configures Pulp's logging system.
"""
from logging import handlers
import logging
import os
import threading


DEFAULT_LOG_LEVEL = logging.INFO
LOG_FORMAT_STRING = 'pulp: %(name)s:%(levelname)s: %(message)s'
LOG_PATH = os.path.join('/', 'dev', 'log')


class CompliantSysLogHandler(handlers.SysLogHandler):
    """
    RFC 5426[0] recommends that we limit the length of our log messages. RFC 3164[1] requires that
    we only include visible characters and spaces in our log messages. Though RFC 3164 is obsoleted
    by 5424[2], Pulp wishes to support older syslog receivers that do not handle newline characters
    gracefully. The tracebacks that Pulp generates can cause problems both due to their length and
    their newlines. This log handler will split messages into multiple messages by newline
    characters (since newline characters aren't handled well) and further by message length. RFC
    5426 doesn't make any specific demands about message length but it appears that our
    target operating systems allow approximately 2041 characters, so we will split there. RFC 5424
    requires that all strings be encoded with UTF-8. Therefore, this
    log handler only accepts unicode strings, or UTF-8 encoded strings.

    [0] https://tools.ietf.org/html/rfc5426#section-3.2
    [1] https://tools.ietf.org/html/rfc3164#section-4.1.3
    [2] https://tools.ietf.org/html/rfc5424#section-6.4
    """
    MAX_MSG_LENGTH = 2041

    @staticmethod
    def _log_id():
        """
        Return a id for a log. Not guaranteed to be unique because threads can be
        recycled, but it can be used to track a single multi line message.
        :return: process id and the last 5 digits of thread id
        :rtype: string
        """
        pid = str(os.getpid())
        tid = str(threading.current_thread().ident)[-5:]
        return "({pid}-{tid}) ".format(pid=pid, tid=tid)

    def emit(self, record):
        """
        This gets called whenever a log message needs to get sent to the syslog. This method will
        inspect the record, and if it contains newlines, it will break the record into multiple
        records. For each of those records, it will also verify that they are no longer than
        MAX_MSG_LENGTH octets. If they are, it will break them up at that boundary as well.

        :param record: The record to be logged via syslog
        :type  record: logging.LogRecord
        """
        if record.exc_info:
            trace = self.formatter.formatException(record.exc_info)
            record.msg += u'\n'
            record.msg += trace.replace('%', '%%')
            record.exc_info = None
        formatter_buffer = self._calculate_formatter_buffer(record)

        if '\n' in record.getMessage():
            msg_id = CompliantSysLogHandler._log_id()
        else:
            msg_id = ""

        for line in record.getMessage().split('\n'):
            for message_chunk in CompliantSysLogHandler._cut_message(line, formatter_buffer,
                                                                     msg_id):
                # We need to use the attributes from record to generate a new record that has
                # mostly the same attributes, but the shorter message. We need to set the args to
                # the empty tuple so that breaking the message up doesn't mess up formatting. This
                # is OK, since record.getMessage() will apply the args to msg for us. exc_info is
                # set to None, as we have already turned any Exceptions into the message
                # that we are now splitting, and we don't want tracebacks to make it past our
                # splitter here because the superclass will transmit newline characters.
                if msg_id and not message_chunk.startswith(msg_id):
                    message_chunk = msg_id + message_chunk

                new_record = logging.LogRecord(
                    name=record.name, level=record.levelno, pathname=record.pathname,
                    lineno=record.lineno, msg=message_chunk, args=tuple(),
                    exc_info=None, func=record.funcName)
                # In Python 2.6 and earlier, the SysLogHandler is not a new-style class. This means
                # that super() cannot be used, so we will just call the SysLogHandler's emit()
                # directly.
                logging.handlers.SysLogHandler.emit(self, new_record)

    def _calculate_formatter_buffer(self, record):
        """
        Given a record with no exc_info, determine how many bytes the formatter will add to it so
        that we know how much room to leave when trimming messages.

        :param record: An example record that can be used to find the formatter buffer
        :type  record: logging.LogRecord
        :return:       The difference between the rendered record length and the message length.
        :rtype:        int
        """
        formatted_record = self.format(record)
        formatted_record = formatted_record.encode('utf8')
        raw_record = record.getMessage()
        raw_record = raw_record.encode('utf8')
        return len(formatted_record) - len(raw_record)

    @staticmethod
    def _cut_message(message, formatter_buffer, msg_id):
        """
        Return a generator of bytes made from message cut at every
        MAX_MSG_LENGTH - formatter_buffer octets, with the exception that it will not cut
        multi-byte characters apart. This method also encodes unicode objects with UTF-8 as a side
        effect, because length limits are specified in octets, not characters.

        :param message:          A message that needs to be broken up if it's too long
        :type  message:          str (Python 2 `unicode`)
        :param formatter_buffer: How many octets of room to leave on each message to account for
                                 extra data that the formatter will add to this message
        :type  formatter_buffer: int
        :param msg_id:           Process and thread id that will be prepended to multi line messages
        :type  msg_id:           string
        :return:                 A generator of bytes objects, each of which is no longer than
                                 MAX_MSG_LENGTH - formatter_buffer octets.
        :rtype:                  generator
        """
        max_length = CompliantSysLogHandler.MAX_MSG_LENGTH - formatter_buffer
        message = message.encode('utf8')

        i = 0
        while i < len(message):
            # The msg either needs to be the max length or the remainder of the
            # message, whichever is shorter
            relative_ending_index = min(max_length, len(message[i:]))

            # Message is longer than allowed length
            if len(message) > i + relative_ending_index:
                msg_id = CompliantSysLogHandler._log_id()

                # Since the remaining message is too long, the correct length of
                # the line is the maximum length - whatever we are prepending.
                relative_ending_index = max_length - len(msg_id)

                # Let's peek one character ahead and see if we are in the middle of a multi-byte
                # character.
                while (ord(message[i + relative_ending_index]) >> 6) == 2:
                    # Any byte of the form 10xxxxxx is a non-leading part of a multi-byte character
                    # in UTF-8. Therefore, we must seek backwards a bit to make sure we don't cut
                    # any multi-byte characters in half.
                    relative_ending_index -= 1

            # The remaining message was not too long by itself, but it is still
            # possible that py prepending msg_id, we will cause overflow.
            elif len(message) > i + relative_ending_index - len(msg_id):
                relative_ending_index = max_length - len(msg_id)

            yield msg_id + message[i:i + relative_ending_index]
            i += relative_ending_index

        if i == 0:
            # If i is still 0, we must have been passed the empty string
            yield ''
