#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
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
import shutil
import unittest
from iniparse import INIConfig

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

from pulp.cds.cdslib import loginit, CdsLib, SecretFile

# test root dir
ROOTDIR = '/tmp/pulp-cds'

# setup logging
loginit(os.path.join(ROOTDIR, 'cds.log'))


class TestCdsPlugin(unittest.TestCase):

    def clean(self):
        shutil.rmtree(ROOTDIR, True)

    def setUp(self):
        config = INIConfig()
        config.cds.packages_dir = os.path.join(ROOTDIR, 'packages')
        config.cds.sync_threads = 3
        self.cds = CdsLib(config)

    def tearDown(self):
        pass

    def test_initialize(self):
        self.cds.initialize()

    def test_release(self):
        self.cds.release()

    def test_secret(self):
        uuid = 'mysecret'
        path = os.path.join(ROOTDIR, 'gofer/.secret')
        secret = SecretFile(path)
        secret.write(uuid)
        f = open(path)
        s = f.read()
        f.close()
        self.assertEqual(uuid, s)
        s = secret.read()
        self.assertEqual(uuid, s)
        secret.delete()
        self.assertFalse(os.path.exists(path))
