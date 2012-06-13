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

from gettext import gettext as _
from M2Crypto import X509
import os

from pulp.client.extensions.extensions import PulpCliCommand

def initialize(context):
    # Add login/logout to the root of the CLI, not in a specific section
    context.cli.add_command(LoginCommand(context))
    context.cli.add_command(LogoutCommand(context))

# -- commands -----------------------------------------------------------------

class LoginCommand(PulpCliCommand):
    """
    Requests credentials from the user and uses them to retrieve a user
    certificate from the server. The certificate is saved according to the
    client-level configuration (not the extension config).
    """

    def __init__(self, context):
        d = _('login and download a session certificate')
        PulpCliCommand.__init__(self, 'login', d, self.login)

        self.context = context

        self.create_option('--username', _('server account username'), aliases=['-u'], required=True)
        self.create_option('--password', _('server account password'), aliases=['-p'], required=True)

    def login(self, **kwargs):
        # Query the server
        username = kwargs['username']
        password = kwargs['password']

        certificate = self.context.server.actions.login(username, password).response_body

        # Save the certificate to the filesystem
        id_cert_dir = self.context.config.get('filesystem', 'id_cert_dir')
        id_cert_dir = os.path.expanduser(id_cert_dir)

        if not os.path.exists(id_cert_dir):
            os.mkdir(id_cert_dir)

        id_cert_name = self.context.config.get('filesystem', 'id_cert_filename')

        cert_filename = os.path.join(id_cert_dir, id_cert_name)

        f = open(cert_filename, 'w')
        f.write(certificate)
        f.close()

        # Parse the certificate to extract the expiration date
        expiration_date = None
        try:
            certificate_section = str(certificate[certificate.index('-----BEGIN CERTIFICATE'):])
            x509_cert = X509.load_cert_string(certificate_section)
            expiration_date = x509_cert.get_not_after()
        except Exception:
            self.context.logger.exception('Could not parse expiration date from certificate')

        # Generate the message based on how successful we were parsing the certificate
        msg = _('Successfully logged in.')
        if expiration_date is not None:
            msg += _(' Session certificate will expire at %(e)s.')
            msg = msg % {'e' : expiration_date}

        self.context.prompt.render_success_message(msg)

class LogoutCommand(PulpCliCommand):
    """
    Removes the user certificate if one exists.
    """
    def __init__(self, context):
        d = _('deletes the user\'s session certificate')
        PulpCliCommand.__init__(self, 'logout', d, self.logout)

        self.context = context

    def logout(self):
        id_cert_dir = self.context.config.get('filesystem', 'id_cert_dir')
        id_cert_dir = os.path.expanduser(id_cert_dir)
        id_cert_name = self.context.config.get('filesystem', 'id_cert_filename')

        cert_filename = os.path.join(id_cert_dir, id_cert_name)

        if os.path.exists(cert_filename):
            os.remove(cert_filename)
            msg  = _('Session certificate successfully removed.')
            self.context.prompt.render_success_message(msg)
        else:
            msg = _('No session certificate found, nothing to do.')
            self.context.prompt.render_paragraph(msg)
