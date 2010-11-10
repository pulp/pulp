#!/usr/bin/python
#
# Pulp Repo management module
#
# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import os
from gettext import gettext as _
from pulp.client.credentials import Credentials
from pulp.client.credentials import Login as LoginBundle
from pulp.client.connection import UserConnection
from pulp.client.core.base import Action, Command

# auth actions ----------------------------------------------------------------

class Login(Action):

    description = _('stores user credentials on this machine')

    def setup_parser(self):
        self.parser.add_option('-u', '--username', dest='username',
                               help=_('pulp account username'))
        self.parser.add_option('-p', '--password', dest='password',
                               help=_('pulp account password'))

    def setup_connections(self):
        # first take into account the new credentials
        Credentials.setuser(self.opts.username, self.opts.password)
        self.authconn = UserConnection()

    def run(self):
        # Retrieve the certificate information from the server
        cert_dict = self.authconn.admin_certificate()
        # Write the certificate data
        bundle = LoginBundle()
        key = cert_dict['private_key']
        crt = cert_dict['certificate']
        bundle.write(key, crt)
        print _('User credentials successfully stored at [%s]') % \
                bundle.root()


class Logout(Action):

    description = _('removes stored user credentials on this machine')

    def run(self):
        # Remove the certificate and private key files
        bundle = LoginBundle()
        bundle.delete()
        print _('User credentials removed from [%s]') % bundle.root()

# auth command ----------------------------------------------------------------

class Auth(Command):

    description = _('stores pulp authentication credentials')
