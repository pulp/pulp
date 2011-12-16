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

import getpass
from gettext import gettext as _

from pulp.client.admin.credentials import Login as LoginBundle
from pulp.client.admin.plugin import AdminPlugin
from pulp.client.api import server
from pulp.client.api.service import ServiceAPI
from pulp.client.api.user import UserAPI
from pulp.client.lib import utils
from pulp.client.pluginlib.command import Action, Command

# login actions ----------------------------------------------------------------

class AuthAction(Action):

    def __init__(self, cfg):
        super(AuthAction, self).__init__(cfg)
        self.user_api = UserAPI()
        self.services_api = ServiceAPI()


class Login(AuthAction):

    description = _('stores user credentials on this machine')
    name = "login"

    def setup_parser(self):
        self.parser.add_option('-u', '--username', dest='username',
                               help=_('pulp account username'))
        self.parser.add_option('-p', '--password', dest='password',
                               help=_('pulp account password'))

    def run(self):
        username = self.get_required_option('username')
        if self.opts.password:
            password = self.opts.password
        else:
            password = getpass.getpass("Enter password: ")
        server.active_server.set_basic_auth_credentials(username, password)
        # Retrieve the certificate information from the server
        crt = self.user_api.admin_certificate()
        # Write the certificate data
        bundle = LoginBundle()
        bundle.write(crt)
        print _('User credentials successfully stored at [%s]') % bundle.crtpath()


class Logout(AuthAction):

    description = _('removes stored user credentials on this machine')
    name = "logout"

    def run(self):
        # Remove the certificate and private key files
        bundle = LoginBundle()
        bundle.delete()
        print _('User credentials removed from [%s]') % bundle.crtpath()

# repo auth actions------------------------------------------------------------

class EnableGlobalRepoAuth(AuthAction):

    description = _('uploads a certificate bundle to be used for global repo authentication')
    name = "enable_global_repo_auth"

    def setup_parser(self):
        self.parser.add_option("--ca", dest="ca",
                               help=_("absolute path to the CA certificate used to validate consumer certificates"))
        self.parser.add_option("--cert", dest="cert",
                               help=_("absolute path to the certificate that will be provided to consumers to grant access to repositories"))
        self.parser.add_option("--key", dest="key",
                               help=_("absolute path to the private key for the consumer certificate"))

    def run(self):

        ca = self.get_required_option('ca')
        ca = utils.readFile(ca)
        cert = self.get_required_option('cert')
        cert = utils.readFile(cert)
        key = self.opts.key # key is optional
        if key:
            key = utils.readFile(key)

        bundle = {'ca'   : ca,
                  'cert' : cert,
                  'key'  : key,
                  }

        self.services_api.enable_global_repo_auth(bundle)
        print _('Global repository authentication enabled')

class DisableGlobalRepoAuth(AuthAction):

    description = _('disables the global repo authentication checks across all repos')
    name = "disable_global_repo_auth"

    def run(self):
        self.services_api.disable_global_repo_auth()
        print _('Global repository authentication disabled')

# auth command ----------------------------------------------------------------

class Auth(Command):

    description = _('stores pulp authentication credentials')
    name = "auth"

    actions = [ Login,
                Logout,
                EnableGlobalRepoAuth,
                DisableGlobalRepoAuth ]

# auth plugin ----------------------------------------------------------------

class AuthPlugin(AdminPlugin):

    name = "auth"
    commands = [ Auth ]
