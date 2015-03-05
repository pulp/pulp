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
import stat
try:
    import kerberos as krb
    import krbV
except ImportError:
    krb = None

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

        self.create_option('--username', _('server account username'), aliases=['-u'], required=False)
        self.create_option('--password', _('server account password'), aliases=['-p'], required=False)

    def login(self, **kwargs):
        for auth_type in ['Kerberos', 'Basic']:
            if auth_type is 'Kerberos':
                if krb is not None and self.has_kerberos_ticket():
                    __, krb_context = krb.authGSSClientInit("HTTP@%s" % self.context.server.server_info.server.host)
                    krb.authGSSClientStep(krb_context, "")
                    negotiate_details = krb.authGSSClientResponse(krb_context)
                    #logger.info("KERBEROS selected - %s" % krbV.default_context().default_ccache().principal())
                    username = krbV.default_context().default_ccache().principal()
                    password = None
                else:
                    continue
            if auth_type is 'Basic':
                # Query the server
                username = kwargs['username']
                password = kwargs['password']
                # Hidden, interactive prompt for the password if not specified

                if username is None:
                    self.context.prompt.write(_('No username provided'))
                    return os.EX_NOUSER

                if password is None:
                    prompt_msg = 'Enter password: '
                    password = self.context.prompt.prompt_password(_(prompt_msg))
                    if password is self.context.prompt.ABORT:
                        self.context.prompt.render_spacer()
                        self.context.prompt.write(_('Login cancelled'))
                        return os.EX_NOUSER
           
            #result = self.context.server.actions.login(username, password).response_body
            try:
                response = self.context.server.actions.login(username, password)
                break
            except Exception:
                continue

        result = response.response_body
        key_cert = result['key'] + result['certificate']

        # Save the certificate to the filesystem
        id_cert_dir = self.context.config['filesystem']['id_cert_dir']
        id_cert_dir = os.path.expanduser(id_cert_dir)

        if not os.path.exists(id_cert_dir):
            os.mkdir(id_cert_dir)

        id_cert_name = self.context.config['filesystem']['id_cert_filename']

        cert_filename = os.path.join(id_cert_dir, id_cert_name)

        #Create the certificate file with user access only permissions 0600
        mode = stat.S_IRUSR | stat.S_IWUSR
        f = os.fdopen(os.open(cert_filename, os.O_WRONLY | os.O_CREAT, mode), 'w')
        try:
            f.write(key_cert)
        finally:
            f.close()

        # Parse the certificate to extract the expiration date
        expiration_date = None
        try:
            certificate_section = str(key_cert[key_cert.index('-----BEGIN CERTIFICATE'):])
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
    
    def has_kerberos_ticket(self):
        """
        Verify if the user has a valid Kerberos ticket.

        :rtype: boolean
        """
        ctx = krbV.default_context()
        cc = ctx.default_ccache()
        try:
            printc = cc.principal()
            retval = True
        except krbV.Krb5Error:
            retval = False
        return retval


class LogoutCommand(PulpCliCommand):
    """
    Removes the user certificate if one exists.
    """
    def __init__(self, context):
        d = _('deletes the user\'s session certificate')
        PulpCliCommand.__init__(self, 'logout', d, self.logout)

        self.context = context

    def logout(self):
        id_cert_dir = self.context.config['filesystem']['id_cert_dir']
        id_cert_dir = os.path.expanduser(id_cert_dir)
        id_cert_name = self.context.config['filesystem']['id_cert_filename']

        cert_filename = os.path.join(id_cert_dir, id_cert_name)

        if os.path.exists(cert_filename):
            os.remove(cert_filename)
            msg  = _('Session certificate successfully removed.')
            self.context.prompt.render_success_message(msg)
        else:
            msg = _('No session certificate found, nothing to do.')
            self.context.prompt.render_paragraph(msg)
