# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
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
Centralized logic for handling the series of expected exceptions coming from
server operations (i.e. the 400 series of HTTP status codes). The handling
includes displaying consistent error messages and indicating the appropriate
exit code.

The main entry point is the handle_exception call that will detect the type of
error and handle it accordingly.

Individual handling methods are also available in the event an extension needs
to catch and display an exception using the consistent formatting but still
react to it in the extension itself.
"""

from gettext import gettext as _
import logging
import os

from pulp.gc_client.api.exceptions import *
from pulp.gc_client.util.arg_utils import InvalidConfig

# -- constants ----------------------------------------------------------------

CODE_BAD_REQUEST = os.EX_DATAERR
CODE_NOT_FOUND = os.EX_DATAERR
CODE_CONFLICT = os.EX_DATAERR
CODE_PULP_SERVER_EXCEPTION = os.EX_SOFTWARE
CODE_CONNECTION_EXCEPTION = os.EX_IOERR
CODE_PERMISSIONS_EXCEPTION = os.EX_NOPERM
CODE_UNEXPECTED = os.EX_SOFTWARE
CODE_INVALID_CONFIG = os.EX_DATAERR

LOG = logging.getLogger(__name__)

# -- classes ------------------------------------------------------------------

class ExceptionHandler:
    def __init__(self, prompt, config):
        """
        :param prompt: prompt instance used to display error messages
        :type  prompt: Prompt

        :param config: client configuration
        :type  config: ConfigParser
        """
        self.prompt = prompt
        self.config = config

    def handle_exception(self, e):
        """
        Analyzes the type of exception passed in and calls the appropriate
        method to handle it.

        @param e:
        @return:
        """

        # Determine which method to call based on exception type
        mappings = (
            (BadRequestException,  self.handle_bad_request),
            (NotFoundException,    self.handle_not_found),
            (ConflictException,    self.handle_conflict),
            (PulpServerException,  self.handle_server_error),
            (ConnectionException,  self.handle_connection_error),
            (PermissionsException, self.handle_permission),
            (InvalidConfig,        self.handle_invalid_config),
        )

        handle_func = self.handle_unexpected
        for exception_type, func in mappings:
            if isinstance(e, exception_type):
                handle_func = func
                break

        exit_code = handle_func(e)
        return exit_code

    def handle_bad_request(self, e):
        """
        Handles any bad request (HTTP 400) error from the server. Based on the
        data included the error message will indicate details on what caused
        the error.

        @return: appropriate exit code for this error
        """

        self._log_server_exception(e)

        # The following keys may be present to further classify the exception:
        # property_names - values for these properties were invalid
        # missing_property_names - required properties that were not specified

        if 'property_names' in e.extra_data:
            msg = 'The values for the following properties were invalid: %(p)s'
            msg = _(msg) % {'p' : ', '.join(e.extra_data['property_names'])}
        elif 'missing_property_names' in e.extra_data:
            msg = 'The following properties are required but were not provided: %(p)s'
            msg = _(msg) % {'p' : ', '.join(e.extra_data['missing_property_names'])}
        else:
            msg = 'The server indicated one or more values were incorrect. The server ' \
                  'provided the following error message:'
            self.prompt.render_failure_message(_(msg))

            self.prompt.render_failure_message('   %s' % e.error_message)
            msg = 'More information can be found in the client log file %(l)s.'
            msg = _(msg) % {'l' : self._log_filename()}

        self.prompt.render_failure_message(msg)
        return CODE_BAD_REQUEST

    def handle_not_found(self, e):
        """
        Handles a not found (HTTP 404) error from the server.

        @return: appropriate exit code for this error
        """

        self._log_server_exception(e)

        # There are no further classifications for this error type

        msg = _('The following resource(s) could not be found:')
        self.prompt.render_failure_message(msg)

        msg = ''
        for resource_type, resource_id in e.extra_data['resources'].items():
            msg += '  %s (%s)\n' % (resource_id, resource_type)

        self.prompt.render_failure_message(msg)

        return CODE_NOT_FOUND

    def handle_conflict(self, e):
        """
        Handles a conflict on the server (HTTP 409). The cause for the 409 will
        be determined based on the included extra data and an appropriate error
        message will be displayed.

        @return: appropriate exit code for this error
        """

        self._log_server_exception(e)

        # There are two classifications for conflicts:
        # resource_id - duplicate resource
        # reasons - conflicting operation

        if 'resource_id' in e.extra_data:
            msg = 'A resource with the ID "%(i)s" already exists.'
            msg = _(msg) % {'i' : e.extra_data['resource_id']}
        elif 'reasons' in e.extra_data:
            msg = 'The requested operation conflicts with one or more operations ' \
                  'already queued for the resource. The following operations on the ' \
                  'specified resources caused the request to be rejected:\n\n'
            msg = _(msg)

            for r in e.extra_data['reasons']:
                msg += _('Resource:  %(t)s - %(i)s\n') % {'t' : r['resource_type'],
                                                       'i' : r['resource_id']}
                msg += _('Operation: %(o)s') % {'o' : r['operation']}
        else:
            msg = 'The requested operation could not execute due to an unexpected ' \
                  'conflict on the server. More information can be found in the ' \
                  'client log file %(l)s.'
            msg = _(msg) % {'l' : self._log_filename()}

        self.prompt.render_failure_message(msg)
        return CODE_CONFLICT

    def handle_server_error(self, e):
        """
        Handles an internal server error (HTTP 50x).

        @return: appropriate exit code for this error
        """

        self._log_server_exception(e)

        # This is a very vague error condition; the best we can do is rely on
        # the exception dump to the log file

        msg = 'An internal error occurred on the Pulp server. More information ' \
              'can be found in the client log file %(l)s.'
        msg = _(msg) % {'l' : self._log_filename()}

        self.prompt.render_failure_message(msg)
        return CODE_PULP_SERVER_EXCEPTION

    def handle_connection_error(self, e):
        """
        Handles a connection error coming out of the client's HTTP libraries.

        @return: appropriate exit code for this error
        """

        self._log_client_exception(e)

        msg = 'An error occurred attempting to contact the server. More information ' \
              'can be found in the client log file %(l)s.'
        msg = _(msg) % {'l' : self._log_filename()}

        self.prompt.render_failure_message(msg)
        return CODE_CONNECTION_EXCEPTION

    def handle_permission(self, e):
        """
        Handles an authentication error from the server.

        @return: appropriate exit code for this error
        """

        self._log_client_exception(e)

        msg = 'Authentication failed.'

        desc = 'This may occur if the user certificate has ' \
               'expired. Please logout to remove the certificate and login again. ' \
               'If credentials were specified, please double check the username and ' \
               'password and attempt the request again.'

        self.prompt.render_failure_message(_(msg))
        self.prompt.render_paragraph(_(desc))

        return CODE_PERMISSIONS_EXCEPTION

    def handle_invalid_config(self, e):
        """
        Handles a client-side argument parsing exception.

        @return: appropriate exit code for this error
        """

        self._log_client_exception(e)

        self.prompt.render_failure_message(e[0])
        return CODE_INVALID_CONFIG

    def handle_unexpected(self, e):
        """
        Catch-all to handle any exception that wasn't explicitly handled by
        any of the other handle_* methods in this class.

        @return: appropriate exit code for this error
        """

        self._log_client_exception(e)

        msg = 'An unexpected error has occurred. More information '\
              'can be found in the client log file %(l)s.'
        msg = _(msg) % {'l' : self._log_filename()}

        self.prompt.render_failure_message(msg)
        return CODE_UNEXPECTED

    def _log_server_exception(self, e):
        """
        Dumps all information from an exception that came from the server
        to the log.

        @type e: RequestException
        """
        template = """Exception occurred:
        href:      %(h)s
        method:    %(m)s
        status:    %(s)s
        error:     %(e)s
        traceback: %(t)s
        data:      %(d)s
        """

        data = {'h' : e.href,
                'm' : e.http_request_method,
                's' : e.http_status,
                'e' : e.error_message,
                't' : e.traceback,
                'd' : e.extra_data}

        LOG.error(template % data)

    def _log_client_exception(self, e):
        """
        Dumps all information from a client-side originated exception to the log.

        @type e: Exception
        """
        LOG.exception('Client-side exception occurred')

    def _log_filename(self):
        """
        Syntactic sugar for reading the log filename out of the config.

        @return: full path to the log file
        """
        return self.config.get('logging', 'filename')