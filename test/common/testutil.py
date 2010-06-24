#!/usr/bin/python
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

import pulp.util

def load_test_config():
    base_file = os.path.abspath(os.path.dirname(__file__)) + '../../etc/pulp/pulp.ini'
    config = pulp.util.load_config(base_file)

    override_file = os.path.abspath(os.path.dirname(__file__)) + '/test-override-pulp.ini'
    config = pulp.util.load_config(override_file, config=config)

    return config

def create_package(api, name):
    test_pkg_name = name
    test_epoch = "1"
    test_version = "1.2.3"
    test_release = "1.el5"
    test_arch = "x86_64"
    test_description = "test description text"
    test_checksum_type = "sha256"
    test_checksum = "9d05cc3dbdc94150966f66d76488a3ed34811226735e56dc3e7a721de194b42e"
    test_filename = "test-filename-1.2.3-1.el5.x86_64.rpm"
    p = api.package_by_ivera(name, test_version, test_epoch, test_release, test_arch)
    if (p == None):    
        p = api.create(name=test_pkg_name, epoch=test_epoch, version=test_version, 
            release=test_release, arch=test_arch, description=test_description, 
            checksum_type="sha256", checksum=test_checksum, filename=test_filename)
        lookedUp = api.package(p['id'])
        return lookedUp
    else:
        return p
    