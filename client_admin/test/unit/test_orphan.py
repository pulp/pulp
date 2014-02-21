# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from pulp.client.admin import orphan
from pulp.devel.unit import base


class TestOrphanSection(base.PulpClientTests):
    def setUp(self):
        super(TestOrphanSection, self).setUp()

        self.section = orphan.OrphanSection(self.context)

    def test_initialize(self):
        orphan.initialize(self.context)

        self.assertEqual(len(self.context.cli.root_section.subsections), 1)
        self.assertTrue(isinstance(self.context.cli.root_section.subsections['orphan'],
                        orphan.OrphanSection))

    def test_adds_commands(self):
        self.assertEqual(len(self.section.commands), 2)
