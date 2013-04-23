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

from gettext import gettext as _
import os
import sys

from M2Crypto import X509

import pulp.client.launcher
from pulp.client.extensions.exceptions import ExceptionHandler, CODE_PERMISSIONS_EXCEPTION
from pulp.common import auth_utils

# -- admin client overrides ---------------------------------------------------

class AdminExceptionHandler(ExceptionHandler):

    def handle_permission(self, e):
        """
        Handles an authentication error from the server.

        @return: appropriate exit code for this error
        """

        self._log_client_exception(e)

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

        # If the certificate exists, parse the expiration date
        id_cert_dir = self.config['filesystem']['id_cert_dir']
        id_cert_dir = os.path.expanduser(id_cert_dir)
        id_cert_name = self.config['filesystem']['id_cert_filename']
        full_cert_path = os.path.join(id_cert_dir, id_cert_name)

        expiration_date = None
        try:
            f = open(full_cert_path, 'r')
            certificate = f.read()
            f.close()

            certificate_section = str(certificate[certificate.index('-----BEGIN CERTIFICATE'):])
            x509_cert = X509.load_cert_string(certificate_section)
            expiration_date = x509_cert.get_not_after()
        except Exception:
            # Leave the expiration_date as None and show generic login message
            pass

        if expiration_date:
            desc = _('The session certificate expired on %(e)s. Use the login '
                     'command to begin a new session.')
            desc = desc % {'e' : expiration_date}
        else:
            desc = _('Use the login command to authenticate with the server and '
                     'download a session certificate for use in future calls to this script. '
                     'If credentials were specified, please double check the username and '
                     'password and attempt the request again.')
            desc = desc

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

# -- script execution ---------------------------------------------------------

def main():
    # Default static config
    config_files = ['/etc/pulp/admin/admin.conf']

    # Any conf.d entries
    conf_d_dir = '/etc/pulp/admin/conf.d'
    config_files += [os.path.join(conf_d_dir, i) for i in sorted(os.listdir(conf_d_dir))]

    # Local user overrides
    override = os.path.expanduser('~/.pulp/admin.conf')
    if os.path.exists(override):
        config_files.append(override)

    exit_code = pulp.client.launcher.main(
        config_files, exception_handler_class=AdminExceptionHandler
    )
    sys.exit(exit_code)
