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
import sys
from gettext import gettext as _

from pulp.client import auth_utils
from pulp.client.connection import UserConnection
from pulp.client.core.base import BaseCore, Action


class AuthAction(Action):

    def connections(self):
        return {'authconn': UserConnection}


class Login(AuthAction):

    def run(self):
        if not self.command_opts.username and not self.command_opts.password:
            print _("username and password are required; try --help")
            sys.exit(1)
        # Retrieve the certificate information from the server
        cert_dict = self.authconn.admin_certificate()
        # Determine the destination and store the cert information there
        if not os.path.exists(auth_utils.admin_cert_dir()):
            os.makedirs(auth_utils.admin_cert_dir())
        # Write the certificate data
        cert_filename, key_filename = auth_utils.admin_cert_paths()
        f = open(cert_filename, 'w')
        f.write(cert_dict['certificate'])
        f.close()
        f = open(key_filename, 'w')
        f.write(cert_dict['private_key'])
        f.close()
        print _('user credentials successfully stored at [%s]') % \
            auth_utils.admin_cert_dir()


class Logout(AuthAction):

    def run(self):
        # Determine the destination and store the cert information there
        cert_filename, key_filename = auth_utils.admin_cert_paths()
        # Remove the certificate and private key files
        if os.path.exists(cert_filename):
            os.remove(cert_filename)
        if os.path.exists(key_filename):
            os.remove(key_filename)
        print _('user credentials removed from [%s]') % auth_utils.admin_cert_dir()


class Auth(BaseCore):

    _default_actions = {
        'login': 'stores user credentials on this machine',
        'logout': 'removes stored user credentials on this machine',
    }

    def __init__(self, name='auth', actions=_default_actions):
        super(Auth, self).__init__(name, actions)
        self.login = Login()
        self.logout = Logout()

    def short_description(self):
        return 'stores authentication credentials for the user on the machine'


command_class = auth = Auth
