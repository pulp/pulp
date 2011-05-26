#!/usr/bin/python
#
# Pulp Repo management module
#
# Copyright (c) 2011 Red Hat, Inc.
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

from pulp.client import server
from pulp.client import utils
from pulp.client.api.user import UserAPI
from pulp.client.api.service import ServiceAPI
from pulp.client.credentials import Login as LoginBundle
from pulp.client.core.base import Action, Command

# login actions ----------------------------------------------------------------

class Login(Action):

    description = _('stores user credentials on this machine')

    def __init__(self):
        super(Login, self).__init__()
        self.user_api = UserAPI()

    def setup_parser(self):
        self.parser.add_option('-u', '--username', dest='username',
                               help=_('pulp account username'))
        self.parser.add_option('-p', '--password', dest='password',
                               help=_('pulp account password'))

    def run(self):
        # first take into account the new credentials
        if not server.active_server.has_credentials_set():
            username = self.get_required_option('username')
            password = self.get_required_option('password')
            server.active_server.set_basic_auth_credentials(username, password)
        # Retrieve the certificate information from the server
        cert_dict = self.user_api.admin_certificate()
        # Write the certificate data
        bundle = LoginBundle()
        key = cert_dict['private_key']
        crt = cert_dict['certificate']
        bundle.write(key, crt)
        print _('User credentials successfully stored at [%s]') % bundle.root()


class Logout(Action):

    description = _('removes stored user credentials on this machine')

    def run(self):
        # Remove the certificate and private key files
        bundle = LoginBundle()
        bundle.delete()
        print _('User credentials removed from [%s]') % bundle.root()

# repo auth actions------------------------------------------------------------

class EnableGlobalRepoAuth(Action):

    description = _('uploads a certificate bundle to be used for global repo authentication')

    def __init__(self):
        super(EnableGlobalRepoAuth, self).__init__()
        self.services_api = ServiceAPI()

    def setup_parser(self):
        self.parser.add_option("--ca", dest="ca",
                               help=_("absolute path to the CA certificate used to validate consumer certificates"))
        self.parser.add_option("--cert", dest="cert",
                               help=_("absolute path to the certificate that will be provided to consumers to grant access to repositories"))
        self.parser.add_option("--key", dest="key",
                               help=_("absolute path to the private key for the consumer certificate"))

    def run(self):

        ca_filename = self.get_required_option('ca')
        cert_filename = self.get_required_option('cert')
        key_filename = self.get_required_option('key')

        bundle = {'ca'   : utils.readFile(ca_filename),
                  'cert' : utils.readFile(cert_filename),
                  'key'  : utils.readFile(key_filename),
                  }

        self.services_api.enable_global_repo_auth(bundle)
        print _('Global repository authentication enabled')

class DisableGlobalRepoAuth(Action):

    description = _('disables the global repo authentication checks across all repos')

    def __init__(self):
        super(DisableGlobalRepoAuth, self).__init__()
        self.services_api = ServiceAPI()

    def run(self):
        self.services_api.disable_global_repo_auth()
        print _('Global repository authentication disabled')

# auth command ----------------------------------------------------------------

class Auth(Command):

    description = _('stores pulp authentication credentials')
