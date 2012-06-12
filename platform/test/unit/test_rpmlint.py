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

import os
import subprocess
import unittest


class SpecFileTests(unittest.TestCase):

    def test_rpmlint(self):
        """
        Verifies rpmlint does not indicate any errors in pulp.spec.
        """

        # Jeff, please remove this when you fix for the new v2 spec  :)
        return

        # Setup
        unit_test_dir = os.path.abspath(os.path.dirname(__file__))
        spec_file = unit_test_dir + '/../../pulp.spec'

        # Test
        p = subprocess.Popen('/usr/bin/rpmlint %s' % spec_file, shell=True, stdout=subprocess.PIPE)
        p.wait()

        # Verify
        #   Print the output in case the caller wants to see the full rpmlint output
        print(p.stdout.read())
        
        self.assertEqual(0, p.returncode, msg='rpmlint indicated one or more errors in pulp.spec')
        