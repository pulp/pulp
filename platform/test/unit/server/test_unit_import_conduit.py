# -*- coding: utf-8 -*-
# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import base

from pulp.plugins.conduits import mixins, unit_import


class ImportUnitConduitTests(base.PulpServerTests):

    def setUp(self):
        super(ImportUnitConduitTests, self).setUp()

        self.source_repo_id = 'source-repo'
        self.dest_repo_id = 'dest-repo'
        self.source_importer_id = 'source-imp'
        self.dest_importer_id = 'dest-imp'
        self.association_owner_type = 'ass-type'
        self.association_owner_id = 'ass-id'

        self.conduit = unit_import.ImportUnitConduit(self.source_repo_id, self.dest_repo_id,
                                                     self.source_importer_id, self.dest_importer_id,
                                                     self.association_owner_type, self.association_owner_id)

    def test_mixin_structure(self):
        base_classes = unit_import.ImportUnitConduit.__bases__
        self.assertEqual(5, len(base_classes))

        self.assertTrue(mixins.AddUnitMixin in base_classes)
        self.assertTrue(mixins.ImporterScratchPadMixin in base_classes)
        self.assertTrue(mixins.RepoScratchPadMixin in base_classes)
        self.assertTrue(mixins.SearchUnitsMixin in base_classes)
        self.assertTrue(mixins.SingleRepoUnitsMixin in base_classes)
