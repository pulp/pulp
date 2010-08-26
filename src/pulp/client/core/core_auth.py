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

from pulp.client.logutil import getLogger
from pulp.client.config import Config
from pulp.client.connection import UserConnection
from pulp.client.core.basecore import BaseCore

import gettext
_ = gettext.gettext
log = getLogger(__name__)


CFG = Config()
PULP_DIR = '.pulp'
CERT_FILENAME = 'admin-cert.pem'
KEY_FILENAME = 'admin-key.pem'


class auth(BaseCore):
   
    def __init__(self):
        usage = 'usage: %prog auth [OPTIONS]'
        shortdesc = 'stores authentication credentials for the user on the machine.'
        desc = ''

        self.name = 'auth'
        self.actions = {'login' : 'Stores user credentials on this machine',
                        'logout': 'Removes stored user credentials on this machine',}
        self.is_admin = True

        BaseCore.__init__(self, 'auth', usage, shortdesc, desc)

    def load_server(self):
        self.authconn = UserConnection(host=CFG.server.host or "localhost",
                                       port=CFG.server.port or 443,
                                       username=self.username,
                                       password=self.password)

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
        dest_dir = os.path.join(os.environ['HOME'], PULP_DIR)

        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)

        # Write the certificate data
        cert_filename = os.path.join(dest_dir, CERT_FILENAME)
        key_filename = os.path.join(dest_dir, KEY_FILENAME)

        f = open(cert_filename, 'w')
        f.write(cert_dict['certificate'])
        f.close()

        f = open(key_filename, 'w')
        f.write(cert_dict['private_key'])
        f.close()

        print('User credentials successfully stored at [%s]' % dest_dir)

    def _logout(self):
        # Determine the destination and store the cert information there
        dest_dir = os.path.join(os.environ['HOME'], PULP_DIR)

        cert_filename = os.path.join(dest_dir, CERT_FILENAME)
        key_filename = os.path.join(dest_dir, KEY_FILENAME)

        # Remove the certificate and private key files
        if os.path.exists(cert_filename):
            os.remove(cert_filename)

        if os.path.exists(key_filename):
            os.remove(key_filename)

        print('User credentials removed from [%s]' % dest_dir)
