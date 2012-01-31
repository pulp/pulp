#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

# Python
import logging
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

import pulp.server.util
from pulp.server.auditing import audit

logging.root.setLevel(logging.DEBUG)
qpid = logging.getLogger('qpid.messaging')
qpid.setLevel(logging.ERROR)

class TestAudit(testutil.PulpAsyncTest):

    @audit()
    def dummyFunc(self, descrp):
        pass

    def testProblemPkgImport(self):
        # Problem was seen with 'description'
        # 'description' was of type 'str' not 'unicode'
        # 'description' contained a "registred" symbol
        # @audit resulted in package import failures
        dir = os.path.join(self.data_path, "non_ascii_descrip")
        package_list = pulp.server.util.get_repo_packages(dir)
        for pkg in package_list:
            self.dummyFunc(pkg.description)
        self.assertTrue(True)
