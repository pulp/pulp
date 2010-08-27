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


PULP_DIR = '.pulp'
CERT_FILENAME = 'admin-cert.pem'
KEY_FILENAME = 'admin-key.pem'


def admin_cert_paths():
    '''
    Returns the current user's specific location to admin certificates.

    @return: tuple of the full path to the certificate and full path to the private key
    @rtype:  (string, string)
    '''

    dest_dir = os.path.join(os.environ['HOME'], PULP_DIR)
    cert_filename = os.path.join(dest_dir, CERT_FILENAME)
    key_filename = os.path.join(dest_dir, KEY_FILENAME)

    return cert_filename, key_filename
