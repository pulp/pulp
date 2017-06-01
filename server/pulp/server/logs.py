"""
This module defines and configures Pulp's logging system.
"""
import ConfigParser
import logging
import os
import sys
import threading

from celery.signals import setup_logging

from pulp.server import config
from pulp.server.async.tasks import get_current_task_id


DEFAULT_LOG_LEVEL = logging.INFO
# A list of modules from which we silence all log messages. It might be possible to expand this data
# structure to express log levels to blacklist as well, if we ever find that we need that in the
# future.
LOG_BLACKLIST = ['qpid.messaging.io.ops', 'qpid.messaging.io.raw']
LOG_FORMAT_STRING = 'pulp: %(name)s:%(levelname)s: %(message)s'
TASK_LOG_FORMAT_STRING = 'pulp: %(name)s:%(levelname)s: [%(task_id)-8s] %(message)s'
LOG_PATH = os.path.join('/', 'dev', 'log')
VALID_LOGGERS = ['syslog', 'console']


def _blacklist_loggers():
    """
    Disable all the loggers in the LOG_BLACKLIST.
    """
    for logger_name in LOG_BLACKLIST:
        logger = logging.getLogger(logger_name)
        logger.disabled = True
        logger.propagate = False

def get_log_type():
    log_type = config.config.get('server', 'log_type')
    if log_type not in VALID_LOGGERS:
        print >> sys.stderr, "log_type not properly set. Defaulting to syslog."
        log_type = 'syslog'

    if log_type == 'syslog':
        if not os.path.exists(LOG_PATH):
            print >> sys.stderr, "Unable to access to log, {log_path}.".format(log_path=LOG_PATH)
            sys.exit(os.EX_UNAVAILABLE)

    return log_type

def get_log_level():
    log_level = None

    try:
        log_level = config.config.get('server', 'log_level')
        log_level = getattr(logging, log_level.upper())
    except (ConfigParser.NoOptionError, AttributeError):
        # If the user didn't provide a log level, or if they provided an invalid one, let's use the
        # default log level
        log_level = DEFAULT_LOG_LEVEL

    return log_level

@setup_logging.connect
def start_logging(*args, **kwargs):
    """
    Configure Pulp's syslog handler for the configured log level.

    :param args:   Unused
    :type  args:   list
    :param kwargs: Unused
    :type  kwargs: dict
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(get_log_level())

    log_type = get_log_type()
    # Set up our handler and add it to the root logger
    if log_type == 'syslog':
        if not os.path.exists(LOG_PATH):
            print >> sys.stderr, "Unable to access to log, {log_path}.".format(log_path=LOG_PATH)
            sys.exit(os.EX_UNAVAILABLE)

        handler = CompliantSysLogHandler(
            address=LOG_PATH,
            facility=CompliantSysLogHandler.LOG_DAEMON
        )

    elif log_type == 'console':
        handler = logging.StreamHandler()

    task_filter = TaskIDFilter()
    handler.addFilter(task_filter)
    formatter = TaskLogFormatter()
    handler.setFormatter(formatter)
    root_logger.handlers = []
    root_logger.addHandler(handler)

    try:
        # Celery uses warnings so let's capture those with this logger too. captureWarnings is new
        # in Python 2.7, which is why we want to catch the AttributeError and move on.
        logging.captureWarnings(True)
    except AttributeError:
        pass

    _blacklist_loggers()


def stop_logging():
    """
    Informs the logging system to perform an orderly shutdown by flushing and closing all handlers.
    This should be called at application exit and no further use of the logging system should be
    made after this call.
    """
    logging.shutdown()
    root_logger = logging.getLogger()
    root_logger.handlers = []


class TaskIDFilter(logging.Filter):
    """
    This is a filter which injects the current task id from celery into the log.
    """
    def filter(self, record):
        record.task_id = get_current_task_id()
        return True


class TaskLogFormatter(logging.Formatter):
    """
    This formatter changes format depending on whether there is a task_id in
    the LogRecord
    """
    def format(self, record):
        if record.task_id is None:
            self._fmt = LOG_FORMAT_STRING
        else:
            record.task_id = record.task_id[:8]
            self._fmt = TASK_LOG_FORMAT_STRING
        return logging.Formatter.format(self, record)


class CompliantSysLogHandler(logging.handlers.SysLogHandler):
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
            if not isinstance(record.msg, basestring):
                record.msg = unicode(record.msg)
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

                self.filter(new_record)
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
        if isinstance(formatted_record, unicode):
            formatted_record = formatted_record.encode('utf8')
        raw_record = record.getMessage()
        if isinstance(raw_record, unicode):
            raw_record = raw_record.encode('utf8')
        return len(formatted_record) - len(raw_record)

    @staticmethod
    def _cut_message(message, formatter_buffer, msg_id):
        """
        Return a generator of strings made from message cut at every
        MAX_MSG_LENGTH - formatter_buffer octets, with the exception that it will not cut
        multi-byte characters apart. This method also encodes unicode objects with UTF-8 as a side
        effect, because length limits are specified in octets, not characters.

        :param message:          A message that needs to be broken up if it's too long
        :type  message:          basestring
        :param formatter_buffer: How many octets of room to leave on each message to account for
                                 extra data that the formatter will add to this message
        :type  formatter_buffer: int
        :param msg_id:           Process and thread id that will be prepended to multi line messages
        :type  msg_id:           string
        :return:                 A generator of str objects, each of which is no longer than
                                 MAX_MSG_LENGTH - formatter_buffer octets.
        :rtype:                  generator
        """
        max_length = CompliantSysLogHandler.MAX_MSG_LENGTH - formatter_buffer
        if isinstance(message, unicode):
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
