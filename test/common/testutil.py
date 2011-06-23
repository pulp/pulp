#!/usr/bin/python
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

import os
import random
import unittest
import time
from datetime import timedelta

import mocks

from pulp.server import async
from pulp.repo_auth import repo_cert_utils
from pulp.server import auditing
from pulp.server import config
from pulp.server.api.cds import CdsApi
from pulp.server.api.consumer import ConsumerApi
from pulp.server.api.repo import RepoApi
from pulp.server.db import connection
from pulp.server.db.model import Delta
from pulp.server.db.model.cds import CDSRepoRoundRobin
from pulp.server.logs import start_logging, stop_logging
from pulp.server.util import random_string
from pulp.server.auth.cert_generator import SerialNumber
from pulp.server.tasking.taskqueue import queue
from pulp.server import constants

SerialNumber.PATH = '/tmp/sn.dat'
constants.LOCAL_STORAGE = "/tmp/pulp/"
constants.CACHE_DIR = "/tmp/pulp/cache"

def load_test_config():
    if not os.path.exists('/tmp/pulp'):
        os.makedirs('/tmp/pulp')

    override_file = os.path.abspath(os.path.dirname(__file__)) + '/test-override-pulp.conf'
    override_repo_file = os.path.abspath(os.path.dirname(__file__)) + '/test-override-repoauth.conf'
    stop_logging()
    try:
        config.add_config_file(override_file)
        config.add_config_file(override_repo_file)
    except RuntimeError:
        pass
    start_logging()

    # The repo_auth stuff, which runs outside of the server codebase, needs to know
    # where to look for its config as well
    repo_cert_utils.CONFIG_FILENAME = override_file

    return config.config

def create_package(api, name, version="1.2.3", release="1.el5", epoch="1",
        arch="x86_64", description="test description text",
        checksum_type="sha256",
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
    d = Delta(p, ('requires', 'provides',))
    api.update(p.id, d)
    return p

class PulpTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.mox = mox.Mox()
        mocks.install()
        self.config = load_test_config()
        connection.initialize()
        self.mock_async()

        self.repo_api = RepoApi()
        self.consumer_api = ConsumerApi()
        self.cds_api = CdsApi()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.clean()

    def clean(self):
        '''
        Removes any entities written to the database in all used APIs.
        '''
        self.cds_api.clean()
        self.repo_api.clean()
        self.consumer_api.clean()

        # Flush the assignment algorithm cache
        CDSRepoRoundRobin.get_collection().remove(safe=True)

        auditing.cull_events(timedelta())
        mocks.reset()

    def mock_async(self):
        pass


class PulpAsyncTest(PulpTest):

    def setUp(self):
        PulpTest.setUp(self)
        async.config.config = self.config
        async.initialize()

    def tearDown(self):
        PulpTest.tearDown(self)
        async._queue._cancel_dispatcher()
        async.finalize()

    def mock_async(self):
        pass
