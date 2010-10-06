# -*- coding: utf-8 -*-

# Copyright © 2010 Red Hat, Inc.
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

from pulp.client import auth_utils


# TODO make this configurable
_consumer_id_file = '/etc/pulp/consumer'

_username = None
_password = None
_cert_file = None
_key_file = None
_local_consumer_id = None


def root_check():
    """
    Simple function to assure execution by root.
    """
    if os.getuid() == 0:
        return
    print >> sys.stderr, _('error: must be root to execute')
    sys.exit(os.EX_NOUSER)


def get_username_password():
    return (_username, _password)


def set_username_password(username, password):
    global _username, _password
    assert None not in (username, password)
    _username = username
    _password = password


def get_cert_key_files():
    return (_cert_file, _key_file)


def set_cert_key_files(cert_file, key_file):
    global _cert_file, _key_file
    assert None not in (cert_file, key_file)
    _cert_file = cert_file
    _key_file = key_file


def set_local_cert_key_files():
    global _cert_file, _key_file
    _cert_file, _key_file = auth_utils.admin_cert_paths()


def get_consumer_id():
    return _local_consumer_id


def set_local_consumer_id():
    global _local_consumer_id
    if not os.access(_consumer_id_file, os.F_OK | os.R_OK):
        return False
    try:
        _local_consumer_id = file(_consumer_id_file, 'r').read()
    except IOError, e:
        # TODO log the error
        raise
    else:
        return True
