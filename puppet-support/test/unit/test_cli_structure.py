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

import base_cli

from pulp_puppet.extension.admin import structure

class StructureTests(base_cli.ExtensionTests):

    def test_structure(self):
        # Test
        structure.ensure_structure(self.cli)

        # Verify
        puppet_root_section = self.cli.find_section(structure.SECTION_ROOT)
        self.assertTrue(puppet_root_section is not None)
        self._assert_section(puppet_root_section, structure.STRUCTURE)

    def test_structure_idempotency(self):
        # Test
        structure.ensure_structure(self.cli)
        structure.ensure_structure(self.cli)

        # Verify
        puppet_root_section = self.cli.find_section(structure.SECTION_ROOT)
        self.assertTrue(puppet_root_section is not None)
        self._assert_section(puppet_root_section, structure.STRUCTURE)

    def _assert_section(self, parent, child_dict):
        self.assertTrue(parent is not None)

        for child_name, grandchildren in child_dict.items():
            child_section = parent.find_subsection(child_name)
            self.assertTrue(child_section is not None, msg='Missing section: %s' % child_name)

            self._assert_section(child_section, grandchildren)

class SectionRetrievalTests(base_cli.ExtensionTests):

    def setUp(self):
        super(SectionRetrievalTests, self).setUp()
        structure.ensure_structure(self.cli)

    def test_repo_section(self):
        section = structure.repo_section(self.cli)
        self.assertEqual(section.name, structure.SECTION_REPO)

    def test_repo_copy_section(self):
        section = structure.repo_copy_section(self.cli)
        self.assertEqual(section.name, structure.SECTION_COPY)

    def test_repo_remove_section(self):
        section = structure.repo_remove_section(self.cli)
        self.assertEqual(section.name, structure.SECTION_REMOVE)

    def test_repo_uploads_section(self):
        section = structure.repo_uploads_section(self.cli)
        self.assertEqual(section.name, structure.SECTION_UPLOADS)

    def test_repo_group_section(self):
        section = structure.repo_group_section(self.cli)
        self.assertEqual(section.name, structure.SECTION_GROUP)

    def test_repo_group_members_section(self):
        section = structure.repo_group_members_section(self.cli)
        self.assertEqual(section.name, structure.SECTION_GROUP_MEMBERS)

    def test_repo_sync_section(self):
        section = structure.repo_sync_section(self.cli)
        self.assertEqual(section.name, structure.SECTION_SYNC)

    def test_repo_sync_schedules_section(self):
        section = structure.repo_sync_schedules_section(self.cli)
        self.assertEqual(section.name, structure.SECTION_SYNC_SCHEDULES)

    def test_repo_publish_section(self):
        section = structure.repo_publish_section(self.cli)
        self.assertEqual(section.name, structure.SECTION_PUBLISH)

    def test_repo_publish_schedules_section(self):
        section = structure.repo_publish_schedules_section(self.cli)
        self.assertEqual(section.name, structure.SECTION_PUBLISH_SCHEDULES)