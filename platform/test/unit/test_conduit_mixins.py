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

import mock
import unittest

from pulp.plugins.conduits import mixins
from pulp.plugins.model import Unit, PublishReport
from pulp.server.exceptions import MissingResource
from pulp.server.managers import factory as manager_factory

class RepoScratchPadMixinTests(unittest.TestCase):

    def setUp(self):
        manager_factory.initialize()

        self.repo_id = 'sp-repo'
        self.mixin = mixins.RepoScratchPadMixin(self.repo_id, mixins.ImporterConduitException)

    @mock.patch('pulp.server.managers.repo.cud.RepoManager.get_repo_scratchpad')
    def test_get_repo_scratchpad(self, mock_call):
        # Setup
        mock_call.return_value = 'foo'

        # Test
        sp = self.mixin.get_repo_scratchpad()

        # Verify
        self.assertEqual(sp, 'foo')

    @mock.patch('pulp.server.managers.repo.cud.RepoManager.get_repo_scratchpad')
    def test_get_repo_scratchpad_server_error(self, mock_call):
        # Setup
        mock_call.side_effect = Exception()

        # Test
        self.assertRaises(mixins.ImporterConduitException, self.mixin.get_repo_scratchpad)

    @mock.patch('pulp.server.managers.repo.cud.RepoManager.set_repo_scratchpad')
    def test_set_repo_scratchpad(self, mock_call):
        # Test
        self.mixin.set_repo_scratchpad('foo')

        # Verify
        self.assertEqual(1, mock_call.call_count)
        self.assertEqual(mock_call.call_args[0][0], self.repo_id)
        self.assertEqual(mock_call.call_args[0][1], 'foo')

    @mock.patch('pulp.server.managers.repo.cud.RepoManager.get_repo_scratchpad')
    def test_set_repo_scratchpad_server_error(self, mock_call):
        # Setup
        mock_call.side_effect = Exception()

        # Test
        self.assertRaises(mixins.ImporterConduitException, self.mixin.set_repo_scratchpad, 'foo')

class SingleRepoUnitsMixinTests(unittest.TestCase):

    def setUp(self):
        manager_factory.initialize()

        self.repo_id = 'sr-repo'
        self.mixin = mixins.SingleRepoUnitsMixin(self.repo_id, mixins.DistributorConduitException)

    @mock.patch('pulp.plugins.types.database.type_definition')
    @mock.patch('pulp.server.managers.repo.unit_association_query.RepoUnitAssociationQueryManager.get_units_across_types')
    def test_get_units(self, mock_query_call, mock_type_def_call):
        # Setup
        mock_query_call.return_value = [
            {'unit_type_id' : 'type-1', 'metadata' : {'m' : 'm1', 'k1' : 'v1'}},
            {'unit_type_id' : 'type-2', 'metadata' : {'m' : 'm1', 'k1' : 'v2'}},
        ]

        mock_type_def_call.return_value = {
            'id' : 'mock-type-def',
            'unit_key' : ['k1']
        }

        fake_criteria = 'fake-criteria'

        # Test
        units = self.mixin.get_units(criteria=fake_criteria)

        # Verify
        self.assertEqual(2, len(units))
        self.assertEqual(1, mock_query_call.call_count)
        self.assertEqual(mock_query_call.call_args[0][0], self.repo_id)
        self.assertEqual(mock_query_call.call_args[1]['criteria'], fake_criteria)

    @mock.patch('pulp.server.managers.repo.unit_association_query.RepoUnitAssociationQueryManager.get_units_across_types')
    def test_get_units_server_error(self, mock_query_call):
        # Setup
        mock_query_call.side_effect = Exception()

        # Test
        self.assertRaises(mixins.DistributorConduitException, self.mixin.get_units)

class MultipleRepoUnitsMixinTests(unittest.TestCase):

    def setUp(self):
        manager_factory.initialize()

        self.mixin = mixins.MultipleRepoUnitsMixin(mixins.ImporterConduitException)

    @mock.patch('pulp.plugins.types.database.type_definition')
    @mock.patch('pulp.server.managers.repo.unit_association_query.RepoUnitAssociationQueryManager.get_units_across_types')
    def test_get_units(self, mock_query_call, mock_type_def_call):
        # Setup
        mock_query_call.return_value = [
                {'unit_type_id' : 'type-1', 'metadata' : {'m' : 'm1', 'k1' : 'v1'}},
                {'unit_type_id' : 'type-2', 'metadata' : {'m' : 'm1', 'k1' : 'v2'}},
        ]

        mock_type_def_call.return_value = {
            'id' : 'mock-type-def',
            'unit_key' : ['k1']
        }

        fake_criteria = 'fake-criteria'

        # Test
        repo_id = 'mr-repo'
        units = self.mixin.get_units(repo_id, criteria=fake_criteria)

        # Verify
        self.assertEqual(2, len(units))
        self.assertEqual(1, mock_query_call.call_count)
        self.assertEqual(mock_query_call.call_args[0][0], repo_id)
        self.assertEqual(mock_query_call.call_args[1]['criteria'], fake_criteria)

    @mock.patch('pulp.server.managers.repo.unit_association_query.RepoUnitAssociationQueryManager.get_units_across_types')
    def test_get_units_server_error(self, mock_query_call):
        # Setup
        mock_query_call.side_effect = Exception()

        # Test
        self.assertRaises(mixins.ImporterConduitException, self.mixin.get_units, 'foo')

class ImporterScratchPadMixinTests(unittest.TestCase):

    def setUp(self):
        manager_factory.initialize()

        self.repo_id = 'isp-repo'
        self.importer_id = 'isp-importer'
        self.mixin = mixins.ImporterScratchPadMixin(self.repo_id, self.importer_id)

    @mock.patch('pulp.server.managers.repo.importer.RepoImporterManager.get_importer_scratchpad')
    def test_get_scratchpad(self, mock_call):
        # Setup
        mock_call.return_value = 'sp'

        # Test
        sp = self.mixin.get_scratchpad()

        # Verify
        self.assertEqual(sp, 'sp')
        self.assertEqual(1, mock_call.call_count)

    @mock.patch('pulp.server.managers.repo.importer.RepoImporterManager.get_importer_scratchpad')
    def test_get_scratchpad_server_error(self, mock_call):
        # Setup
        mock_call.side_effect = Exception()

        # Test
        self.assertRaises(mixins.ImporterConduitException, self.mixin.get_scratchpad)

    @mock.patch('pulp.server.managers.repo.importer.RepoImporterManager.set_importer_scratchpad')
    def test_set_scratchpad(self, mock_call):
        # Test
        self.mixin.set_scratchpad('foo')

        # Verify
        self.assertEqual(1, mock_call.call_count)
        self.assertEqual(mock_call.call_args[0][0], self.repo_id)
        self.assertEqual(mock_call.call_args[0][1], 'foo')

    @mock.patch('pulp.server.managers.repo.importer.RepoImporterManager.set_importer_scratchpad')
    def test_set_scratchpad_server_error(self, mock_call):
        # Setup
        mock_call.side_effect = Exception()

        # Test
        self.assertRaises(mixins.ImporterConduitException, self.mixin.set_scratchpad, 'foo')

class DistributorScratchPadMixinTests(unittest.TestCase):

    def setUp(self):
        manager_factory.initialize()

        self.repo_id = 'dsp-repo'
        self.distributor_id = 'dsp-distributor'
        self.mixin = mixins.DistributorScratchPadMixin(self.repo_id, self.distributor_id)

    @mock.patch('pulp.server.managers.repo.distributor.RepoDistributorManager.get_distributor_scratchpad')
    def test_get_scratchpad(self, mock_call):
        # Setup
        mock_call.return_value = 'sp'

        # Test
        sp = self.mixin.get_scratchpad()

        # Verify
        self.assertEqual(sp, 'sp')
        self.assertEqual(1, mock_call.call_count)

    @mock.patch('pulp.server.managers.repo.distributor.RepoDistributorManager.get_distributor_scratchpad')
    def test_get_scratchpad_server_error(self, mock_call):
        # Setup
        mock_call.side_effect = Exception()

        # Test
        self.assertRaises(mixins.DistributorConduitException, self.mixin.get_scratchpad)

    @mock.patch('pulp.server.managers.repo.distributor.RepoDistributorManager.set_distributor_scratchpad')
    def test_set_scratchpad(self, mock_call):
        # Test
        self.mixin.set_scratchpad('foo')

        # Verify
        self.assertEqual(1, mock_call.call_count)
        self.assertEqual(mock_call.call_args[0][0], self.repo_id)
        self.assertEqual(mock_call.call_args[0][1], self.distributor_id)
        self.assertEqual(mock_call.call_args[0][2], 'foo')

    @mock.patch('pulp.server.managers.repo.distributor.RepoDistributorManager.set_distributor_scratchpad')
    def test_set_scratchpad_server_error(self, mock_call):
        # Setup
        mock_call.side_effect = Exception()

        # Test
        self.assertRaises(mixins.DistributorConduitException, self.mixin.set_scratchpad, 'foo')

class RepoGroupDistributorScratchPadMixinTests(unittest.TestCase):

    def setUp(self):
        manager_factory.initialize()

        self.group_id = 'group-id'
        self.distributor_id = 'group-dist'
        self.mixin = mixins.RepoGroupDistributorScratchPadMixin(self.group_id, self.distributor_id)

    @mock.patch('pulp.server.managers.repo.group.distributor.RepoGroupDistributorManager.get_distributor_scratchpad')
    def test_get_scratchpad(self, mock_call):
        # Setup
        mock_call.return_value = 'sp'

        # Test
        sp = self.mixin.get_scratchpad()

        # Verify
        self.assertEqual(sp, 'sp')
        self.assertEqual(1, mock_call.call_count)
        self.assertEqual(mock_call.call_args[0][0], self.group_id)
        self.assertEqual(mock_call.call_args[0][1], self.distributor_id)

    @mock.patch('pulp.server.managers.repo.group.distributor.RepoGroupDistributorManager.get_distributor_scratchpad')
    def test_get_scratchpad_server_error(self, mock_call):
        # Setup
        mock_call.side_effect = Exception()

        # Test
        self.assertRaises(mixins.DistributorConduitException, self.mixin.get_scratchpad)

    @mock.patch('pulp.server.managers.repo.group.distributor.RepoGroupDistributorManager.set_distributor_scratchpad')
    def test_set_scratchpad(self, mock_call):
        # Test
        self.mixin.set_scratchpad('foo')

        # Verify
        self.assertEqual(1, mock_call.call_count)
        self.assertEqual(mock_call.call_args[0][0], self.group_id)
        self.assertEqual(mock_call.call_args[0][1], self.distributor_id)
        self.assertEqual(mock_call.call_args[0][2], 'foo')

    @mock.patch('pulp.server.managers.repo.group.distributor.RepoGroupDistributorManager.set_distributor_scratchpad')
    def test_set_scratchpad_server_error(self, mock_call):
        # Setup
        mock_call.side_effect = Exception()

        # Test
        self.assertRaises(mixins.DistributorConduitException, self.mixin.set_scratchpad, 'foo')

class AddUnitMixinTests(unittest.TestCase):

    def setUp(self):
        manager_factory.initialize()

        self.repo_id = 'add-repo'
        self.importer_id = 'add-importer'
        self.association_owner_type = 'importer'
        self.association_owner_id = 'imp-id'

        self.mixin = mixins.AddUnitMixin(self.repo_id, self.importer_id,
                                         self.association_owner_type, self.association_owner_id)

    @mock.patch('pulp.server.managers.content.query.ContentQueryManager.request_content_unit_file_path')
    def test_init_unit(self, mock_file_path_call):
        # Setup
        mock_file_path_call.return_value = '/tmp'

        # Test
        path_unit = self.mixin.init_unit('t', {'k' : 'v'}, {'m' : 'm1'}, '/bar')
        no_path_unit = self.mixin.init_unit('t', {'k' : 'v'}, {'m' : 'm1'}, None)

        # Verify
        self.assertTrue(isinstance(path_unit, Unit))
        self.assertEqual(path_unit.type_id, 't')
        self.assertEqual(path_unit.unit_key, {'k' : 'v'})
        self.assertEqual(path_unit.metadata, {'m' : 'm1'})
        self.assertEqual(path_unit.storage_path, '/tmp')

        self.assertEqual(no_path_unit.storage_path, None)

    @mock.patch('pulp.server.managers.content.query.ContentQueryManager.request_content_unit_file_path')
    def test_init_unit_server_error(self, mock_call):
        # Setup
        mock_call.side_effect = Exception()

        # Test
        self.assertRaises(mixins.ImporterConduitException, self.mixin.init_unit, 't', {'k' : 'v'}, {'m' : 'm1'}, '/bar')

    @mock.patch('pulp.server.managers.content.query.ContentQueryManager.request_content_unit_file_path')
    @mock.patch('pulp.server.managers.content.query.ContentQueryManager.get_content_unit_by_keys_dict')
    @mock.patch('pulp.server.managers.content.cud.ContentManager.update_content_unit')
    @mock.patch('pulp.server.managers.content.cud.ContentManager.add_content_unit')
    @mock.patch('pulp.server.managers.repo.unit_association.RepoUnitAssociationManager.associate_unit_by_id')
    def test_save_unit_new_unit(self, mock_associate, mock_add, mock_update, mock_get, mock_path):
        # Setup
        unit = self.mixin.init_unit('t', {'k' : 'v'}, {'m' : 'm1'}, '/bar')
        mock_get.side_effect = MissingResource()
        mock_add.return_value = 'new-unit-id'

        # Test
        saved = self.mixin.save_unit(unit)

        # Verify
        self.assertEqual(1, mock_get.call_count)
        self.assertEqual(0, mock_update.call_count)
        self.assertEqual(1, mock_add.call_count)
        self.assertEqual(1, mock_associate.call_count)
        self.assertEqual(1, self.mixin._added_count)
        self.assertEqual(0, self.mixin._updated_count)
        self.assertEqual(saved.id, 'new-unit-id')

    @mock.patch('pulp.server.managers.content.query.ContentQueryManager.request_content_unit_file_path')
    @mock.patch('pulp.server.managers.content.query.ContentQueryManager.get_content_unit_by_keys_dict')
    @mock.patch('pulp.server.managers.content.cud.ContentManager.update_content_unit')
    @mock.patch('pulp.server.managers.content.cud.ContentManager.add_content_unit')
    @mock.patch('pulp.server.managers.repo.unit_association.RepoUnitAssociationManager.associate_unit_by_id')
    def test_save_unit_updated_unit(self, mock_associate, mock_add, mock_update, mock_get, mock_path):
        # Setup
        unit = self.mixin.init_unit('t', {'k' : 'v'}, {'m' : 'm1'}, '/bar')
        mock_get.return_value = {'_id' : 'existing'}

        # Test
        saved = self.mixin.save_unit(unit)

        # Verify
        self.assertEqual(1, mock_get.call_count)
        self.assertEqual(1, mock_update.call_count)
        self.assertEqual(0, mock_add.call_count)
        self.assertEqual(1, mock_associate.call_count)
        self.assertEqual(0, self.mixin._added_count)
        self.assertEqual(1, self.mixin._updated_count)
        self.assertEqual(saved.id, 'existing')

    @mock.patch('pulp.server.managers.content.query.ContentQueryManager.request_content_unit_file_path')
    @mock.patch('pulp.server.managers.content.query.ContentQueryManager.get_content_unit_by_keys_dict')
    @mock.patch('pulp.server.managers.content.cud.ContentManager.update_content_unit')
    @mock.patch('pulp.server.managers.content.cud.ContentManager.add_content_unit')
    @mock.patch('pulp.server.managers.repo.unit_association.RepoUnitAssociationManager.associate_unit_by_id')
    def test_save_unit_with_error(self, mock_associate, mock_add, mock_update, mock_get, mock_path):
        # Setup
        mock_get.side_effect = Exception()

        # Test
        self.assertRaises(mixins.ImporterConduitException, self.mixin.save_unit, None)

    @mock.patch('pulp.server.managers.content.cud.ContentManager.link_referenced_content_units')
    def test_link_unit(self, mock_link):
        # Setup
        from_unit = Unit('t1', {'k' : 'v1'}, {'m' : 'm'}, 'p')
        from_unit.id = 'from-unit'
        to_unit = Unit('t2', {'k' : 'v2'}, {'m' : 'm'}, 'p')
        to_unit.id = 'to-unit'

        # Test
        self.mixin.link_unit(from_unit, to_unit)

        # Verify
        self.assertEqual(1, mock_link.call_count)
        self.assertEqual(mock_link.call_args[0][0], from_unit.type_id)
        self.assertEqual(mock_link.call_args[0][1], from_unit.id)
        self.assertEqual(mock_link.call_args[0][2], to_unit.type_id)
        self.assertEqual(mock_link.call_args[0][3], [to_unit.id])

    @mock.patch('pulp.server.managers.content.cud.ContentManager.link_referenced_content_units')
    def test_link_unit_bidirectional(self, mock_link):
        # Setup
        from_unit = Unit('t1', {'k' : 'v1'}, {'m' : 'm'}, 'p')
        from_unit.id = 'from-unit'
        to_unit = Unit('t2', {'k' : 'v2'}, {'m' : 'm'}, 'p')
        to_unit.id = 'to-unit'

        # Test
        self.mixin.link_unit(from_unit, to_unit, bidirectional=True)

        # Verify
        self.assertEqual(2, mock_link.call_count)

        call_1_args = mock_link.call_args_list[0][0]
        self.assertEqual(call_1_args[0], from_unit.type_id)
        self.assertEqual(call_1_args[1], from_unit.id)
        self.assertEqual(call_1_args[2], to_unit.type_id)
        self.assertEqual(call_1_args[3], [to_unit.id])

        call_2_args = mock_link.call_args_list[1][0]
        self.assertEqual(call_2_args[0], to_unit.type_id)
        self.assertEqual(call_2_args[1], to_unit.id)
        self.assertEqual(call_2_args[2], from_unit.type_id)
        self.assertEqual(call_2_args[3], [from_unit.id])

    @mock.patch('pulp.server.managers.content.cud.ContentManager.link_referenced_content_units')
    def test_link_unit_server_error(self, mock_call):
        # Setup
        mock_call.side_effect = Exception()

        # Test
        self.assertRaises(mixins.ImporterConduitException, self.mixin.link_unit, None, None)


class StatusMixinTests(unittest.TestCase):

    def setUp(self):
        manager_factory.initialize()

        self.report_id = 'test-report'
        self.mixin = mixins.StatusMixin(self.report_id, mixins.ImporterConduitException)

    @mock.patch('pulp.server.dispatch.factory.context')
    def test_set_progress(self, mock_call):
        # Setup
        mock_context = mock.Mock()
        mock_call.return_value = mock_context

        # Test
        status = 'status'
        self.mixin.set_progress(status)

        # Verify
        self.assertEqual(1, mock_call.call_count)
        self.assertEqual(1, mock_context.report_progress.call_count)

        call_args = mock_context.report_progress.call_args[0]
        expected_report = {
            self.report_id : status,
        }
        self.assertEqual(call_args[0], expected_report)

    @mock.patch('pulp.server.dispatch.factory.context')
    def test_set_progress_with_exception(self, mock_call):
        # Setup
        mock_call.side_effect = Exception()

        # Test
        self.assertRaises(mixins.ImporterConduitException, self.mixin.set_progress, 'foo')

class PublishReportMixinTests(unittest.TestCase):

    def setUp(self):
        self.mixin = mixins.PublishReportMixin()

    def test_build_reports(self):
        # Setup
        summary = 'summary'
        details = 'details'

        # Test Success Report
        r = self.mixin.build_success_report(summary, details)
        self.assertTrue(isinstance(r, PublishReport))
        self.assertEqual(r.success_flag, True)
        self.assertEqual(r.summary, summary)
        self.assertEqual(r.details, details)

        # Test Failure Report
        r = self.mixin.build_failure_report(summary, details)
        self.assertTrue(isinstance(r, PublishReport))
        self.assertEqual(r.success_flag, False)
        self.assertEqual(r.summary, summary)
        self.assertEqual(r.details, details)