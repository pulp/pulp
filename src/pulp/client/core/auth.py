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

import gettext
import os
import sys

import pulp.client.auth_utils as auth_utils
from pulp.client.config import Config
from pulp.client.connection import UserConnection
from pulp.client.core._base import BaseCore
from pulp.client.logutil import getLogger


CFG = Config()
log = getLogger(__name__)

_ = gettext.gettext


class auth(BaseCore):

    def __init__(self):
        usage = 'usage: %prog auth [OPTIONS]'
        shortdesc = 'stores authentication credentials for the user on the machine.'
        desc = ''

        self.name = 'auth'
        self.actions = {'login' : 'Stores user credentials on this machine',
                        'logout': 'Removes stored user credentials on this machine', }
        self.is_admin = True

        BaseCore.__init__(self, 'auth', usage, shortdesc, desc)

    def load_server(self):
        self.authconn = UserConnection(host=CFG.server.host or "localhost",
                                       port=CFG.server.port or 443,
                                       username=self.username,
                                       password=self.password,
                                       cert_file=self.cert_filename,
                                       key_file=self.key_filename)

    def generate_options(self):
        usage = 'auth'
        self.setup_option_parser(usage, '', True)

    def _do_core(self):
        self.action = self._get_action()
        if self.action == 'login':
            self._login()
        if self.action == 'logout':
            self._logout()

    def _login(self):
        if not self.options.username and not self.options.password:
            print _("username and password are required. Try --help")
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

        print _('User credentials successfully stored at [%s]') % \
            auth_utils.admin_cert_dir()

    def _logout(self):
        # Determine the destination and store the cert information there
        cert_filename, key_filename = auth_utils.admin_cert_paths()

        # Remove the certificate and private key files
        if os.path.exists(cert_filename):
            os.remove(cert_filename)

        if os.path.exists(key_filename):
            os.remove(key_filename)

        print _('User credentials removed from [%s]') % auth_utils.admin_cert_dir()
