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
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.server.content.types import parser, model

# -- test data ---------------------------------------------------------------

VALID_DESCRIPTOR_1 = model.TypeDescriptor('valid_descriptor_1',
"""{"types": [
    {"id" : "rpm",
     "display_name" : "RPM",
     "description" : "Yum RPM package",
     "unique_indexes" : [
         ["name", "version", "release", "arch", "filename", "checksum"]
     ],
     "search_indexes" : [
         ["name", "epoch", "version", "release", "arch"],
         "filename"
     ]}
]}
""")

# -- test cases --------------------------------------------------------------

class ParserTest(testutil.PulpTest):

    def test_parse_single_descriptor_single_type(self):
        """
        Tests the simple success case of loading multiple descriptors with
        valid data.
        """

        # Test
        definitions = parser.parse([VALID_DESCRIPTOR_1])

        # Verify
        self.assertTrue(definitions is not None)
        self.assertEqual(1, len(definitions))
