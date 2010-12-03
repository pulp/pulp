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
import random
from datetime import timedelta

from pulp.server import auditing
from pulp.server import config
from pulp.server.db import connection
from pulp.server.logs import start_logging, stop_logging
from pulp.server.util import random_string

def initialize():
    connection.initialize()
    auditing.initialize()

def load_test_config():

    if not os.path.exists('/tmp/pulp'):
        os.makedirs('/tmp/pulp')

    override_file = os.path.abspath(os.path.dirname(__file__)) + '/test-override-pulp.conf'
    stop_logging()
    try:
        config.add_config_file(override_file)
    except RuntimeError:
        pass
    start_logging()
    # Re-init the database connection so we can pick up settings for the test database
    initialize()
    return config.config


def common_cleanup():
    auditing._clear_crontab()
    auditing.cull_events(timedelta())


def create_package(api, name, version="1.2.3", release="1.el5", epoch="1",
        arch="x86_64", description="test description text",
        checksum_type = "sha256", 
        checksum="9d05cc3dbdc94150966f66d76488a3ed34811226735e56dc3e7a721de194b42e",
        filename="test-filename-1.2.3-1.el5.x86_64.rpm"):
    """
    Returns a SON object representing the package.
    """
    test_pkg_name = name
    test_epoch = epoch
    test_version = version
    test_release = release
    test_arch = arch
    test_description = description
    test_checksum_type = checksum_type
    test_checksum = checksum
    test_filename = filename
    p = api.create(name=test_pkg_name, epoch=test_epoch, version=test_version,
        release=test_release, arch=test_arch, description=test_description,
        checksum_type=checksum_type, checksum=test_checksum, filename=test_filename)
    # We are looking up package trough mongo so we get a SON object to return.
    # instead of returning the model.Package object
    lookedUp = api.package(p['id'])
    return lookedUp
    #p = api.package_by_ivera(name, test_version, test_epoch, test_release, test_arch)
    #if (p == None):
    #    p = api.create(name=test_pkg_name, epoch=test_epoch, version=test_version,
    #        release=test_release, arch=test_arch, description=test_description,
    #        checksum_type=checksum_type, checksum=test_checksum, filename=test_filename)
    #    lookedUp = api.package(p['id'])
    #    return lookedUp
    #else:
    #    return p

def create_random_package(api):
    test_pkg_name = random_string()
    test_epoch = random.randint(0, 2)
    test_version = "%s.%s.%s" % (random.randint(0, 100),
                                random.randint(0, 100), random.randint(0, 100))
    test_release = "%s.el5" % random.randint(0, 10)
    test_arch = "x86_64"
    test_description = ""
    test_requires = []
    test_provides = []
    for x in range(10):
        test_description = test_description + " " + random_string()
        test_requires.append(random_string())
        test_provides.append(random_string())

    test_checksum_type = "sha256"
    test_checksum = "9d05cc3dbdc94150966f66d76488a3ed34811226735e56dc3e7a721de194b42e"
    test_filename = "test-filename-zzz-%s-%s.x86_64.rpm" % (test_version, test_release)
    p = api.create(name=test_pkg_name, epoch=test_epoch, version=test_version,
        release=test_release, arch=test_arch, description=test_description,
        checksum_type="sha256", checksum=test_checksum, filename=test_filename)
    p['requires'] = test_requires
    p['provides'] = test_requires
    api.update(p)
    return p


#implicit initialize
initialize()
