# -*- coding: utf-8 -*-
# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import logging
from gettext import gettext as _

from pulp.client.extensions.exceptions import ExceptionHandler, CODE_PERMISSIONS_EXCEPTION
from pulp.common import auth_utils


_logger = logging.getLogger(__name__)


class AdminExceptionHandler(ExceptionHandler):

    def handle_expired_client_cert(self, e):
        """
        Handles the exception raised when the client certificate has expired.

        :param e: The Exception that was raised
        :type  e: pulp.bindings.exceptions.ClientCertificateExpiredException
        :return:  The exit code to be used.
        :rtype:   int
        """
        exit_code = ExceptionHandler.handle_expired_client_cert(self, e)

        desc = _('Use the login command to authenticate with the server and '
                 'download a new session certificate.')
        self.prompt.render_paragraph(desc)

        return exit_code

    def handle_permission(self, e):
        """
        Handles an authentication error from the server.

        :return: appropriate exit code for this error
        """

        _logger.error(e)

        handlers = {
            auth_utils.CODE_FAILED : self._handle_authentication_failed,
            auth_utils.CODE_PERMISSION : self._handle_permission_error,
            auth_utils.CODE_INVALID_SSL_CERT : self._handle_authentication_failed,
            auth_utils.CODE_USER_PASS : self._handle_invalid_username,
        }

        error_code = auth_utils.get_error_code(e.extra_data)
        handler_method = handlers.get(error_code, self._handle_unknown)
        handler_method()

        return CODE_PERMISSIONS_EXCEPTION

    def _handle_authentication_failed(self):
        msg = _('Authentication Failed')
        desc = _('Use the login command to authenticate with the server and '
                 'download a session certificate for use in future calls to this script. '
                 'If credentials were specified, please double check the username and '
                 'password and attempt the request again.')

        self.prompt.render_failure_message(msg)
        self.prompt.render_paragraph(desc)

    def _handle_permission_error(self):
        msg = _('Insufficient Permissions')
        desc = _('The user does not have the appropriate permissions to execute this command.')

        self.prompt.render_failure_message(msg)
        self.prompt.render_paragraph(desc)

    def _handle_invalid_username(self):
        msg = _('Invalid Username or Password')

        self.prompt.render_failure_message(msg)

    def _handle_unknown(self):
        msg = _('Unknown Authentication Failure')
        desc = _('See the server logs for more information.')

        self.prompt.render_failure_message(msg)
        self.prompt.render_paragraph(desc)
