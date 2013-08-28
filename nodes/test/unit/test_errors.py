# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from unittest import TestCase

from pulp_node.error import *


class TestNodeError(TestCase):

    def test_constructor(self):
        # Test
        ne = NodeError(1, a=1, b=2)
        # Verify
        self.assertEqual(ne.error_id, 1)
        self.assertEqual(ne.details['a'], 1)
        self.assertEqual(ne.details['b'], 2)

    def test_equals(self):
        # Test
        ne_1 = NodeError(1, a=1, b=2)
        ne_2 = NodeError(1, a=1, b=2)
        ne_3 = NodeError(1, a=1, b=20)
        ne_4 = NodeError(2, a=1, b=2)
        # Verify
        self.assertEqual(ne_1, ne_2)
        self.assertNotEqual(ne_1, ne_3)
        self.assertNotEqual(ne_2, ne_4)

    def test_to_dict(self):
        # Test
        ne = NodeError(1, a=1, b=2)
        d = ne.dict()
        # Verify
        self.assertEqual(ne.error_id, d['error_id'])
        self.assertEqual(ne.details, d['details'])

    def test_load(self):
        # Test
        d = dict(error_id=1, details=dict(a=1, b=2))
        ne = NodeError(None)
        ne.load(d)
        # Verify
        self.assertEqual(ne.error_id, 1)
        self.assertEqual(ne.details, dict(a=1, b=2))

    def test_load_failed(self):
        # Test
        d = dict(error_id=1, details=dict(a=1, b=2))
        ne = NodeError(None)
        # Verify
        self.assertRaises(ValueError, ne.load, [])


class TestErrors(TestCase):

    def test_caught_exception(self):
        # Test
        exception = ValueError('must be integer')
        ne = CaughtException(exception, repo_id='repo_1')
        # Verify
        self.assertEqual(ne.error_id, CaughtException.ERROR_ID)
        self.assertEqual(ne.details['message'], str(exception))
        self.assertEqual(ne.details['repo_id'], 'repo_1')
        self.assertTrue(isinstance(str(ne), str))

    def test_purge_orphans(self):
        # Test
        ne = PurgeOrphansError(http_code=401)
        # Verify
        self.assertEqual(ne.error_id, PurgeOrphansError.ERROR_ID)
        self.assertEqual(ne.details['http_code'], 401)
        self.assertTrue(isinstance(str(ne), str))

    def test_repo_sync(self):
        # Test
        ne = RepoSyncRestError(repo_id='repo_1', http_code=401)
        # Verify
        self.assertEqual(ne.error_id, RepoSyncRestError.ERROR_ID)
        self.assertEqual(ne.details['http_code'], 401)
        self.assertEqual(ne.details['repo_id'], 'repo_1')
        self.assertTrue(isinstance(str(ne), str))

    def test_get_bindings(self):
        # Test
        ne = GetBindingsError(http_code=401)
        # Verify
        self.assertEqual(ne.error_id, GetBindingsError.ERROR_ID)
        self.assertEqual(ne.details['http_code'], 401)
        self.assertTrue(isinstance(str(ne), str))

    def test_get_child_units(self):
        # Test
        ne = GetChildUnitsError(repo_id='repo_1')
        # Verify
        self.assertEqual(ne.error_id, GetChildUnitsError.ERROR_ID)
        self.assertEqual(ne.details['repo_id'], 'repo_1')
        self.assertTrue(isinstance(str(ne), str))

    def test_get_parent_units(self):
        # Test
        ne = GetParentUnitsError(repo_id='repo_1')
        # Verify
        self.assertEqual(ne.error_id, GetParentUnitsError.ERROR_ID)
        self.assertEqual(ne.details['repo_id'], 'repo_1')
        self.assertTrue(isinstance(str(ne), str))

    def test_importer_not_installed(self):
        # Test
        ne = ImporterNotInstalled(repo_id='repo_1', type_id='abc')
        # Verify
        self.assertEqual(ne.error_id, ImporterNotInstalled.ERROR_ID)
        self.assertEqual(ne.details['repo_id'], 'repo_1')
        self.assertEqual(ne.details['type_id'], 'abc')
        self.assertTrue(isinstance(str(ne), str))

    def test_distributor_not_installed(self):
        # Test
        ne = DistributorNotInstalled(repo_id='repo_1', type_id='abc')
        # Verify
        self.assertEqual(ne.error_id, DistributorNotInstalled.ERROR_ID)
        self.assertEqual(ne.details['repo_id'], 'repo_1')
        self.assertEqual(ne.details['type_id'], 'abc')
        self.assertTrue(isinstance(str(ne), str))

    def test_manifest_download(self):
        # Test
        url = 'http://redhat.com/manifest'
        ne = ManifestDownloadError(url, message='abc')
        # Verify
        self.assertEqual(ne.error_id, ManifestDownloadError.ERROR_ID)
        self.assertEqual(ne.details['url'], url)
        self.assertEqual(ne.details['message'], 'abc')
        self.assertTrue(isinstance(str(ne), str))

    def test_unit_download(self):
        # Test
        url = 'http://redhat.com/unit_1'
        ne = UnitDownloadError(url, repo_id='repo_1', message='abc')
        # Verify
        self.assertEqual(ne.error_id, UnitDownloadError.ERROR_ID)
        self.assertEqual(ne.details['url'], url)
        self.assertEqual(ne.details['repo_id'], 'repo_1')
        self.assertEqual(ne.details['message'], 'abc')
        self.assertTrue(isinstance(str(ne), str))

    def test_add_unit(self):
        # Test
        ne = AddUnitError(repo_id='repo_1')
        # Verify
        self.assertEqual(ne.error_id, AddUnitError.ERROR_ID)
        self.assertEqual(ne.details['repo_id'], 'repo_1')
        self.assertTrue(isinstance(str(ne), str))

    def test_delete_unit(self):
        # Test
        ne = DeleteUnitError(repo_id='repo_1')
        # Verify
        self.assertEqual(ne.error_id, DeleteUnitError.ERROR_ID)
        self.assertEqual(ne.details['repo_id'], 'repo_1')
        self.assertTrue(isinstance(str(ne), str))

    def test_invalid_manifest(self):
        # Test
        ne = InvalidManifestError()
        # Verify
        self.assertEqual(ne.error_id, InvalidManifestError.ERROR_ID)


class TestErrorList(TestCase):

    def test_append(self):
        # Test
        list_ = ErrorList()
        ne_1 = NodeError(1)
        ne_2 = NodeError(2)
        list_.append(ne_1)
        list_.append(ne_2)
        # Verify
        self.assertEqual(len(list_), 2)
        self.assertTrue(ne_1 in list_)
        self.assertTrue(ne_2 in list_)

    def test_unique_append(self):
        # Test
        list_ = ErrorList()
        ne_1 = NodeError(1)
        ne_2 = NodeError(2)
        list_.append(ne_1)
        list_.append(ne_2)
        list_.append(ne_2)
        # Verify
        self.assertEqual(len(list_), 2)
        self.assertTrue(ne_1 in list_)
        self.assertTrue(ne_2 in list_)

    def test_append_value_error(self):
        # Test
        list_ = ErrorList()
        self.assertRaises(ValueError, list_.append, 1)
        # Verify
        self.assertEqual(len(list_), 0)

    def test_extend(self):
        # Test
        list_ = ErrorList()
        ne = NodeError(1)
        list_.extend([ne])
        # Verify
        self.assertEqual(len(list_), 1)
        self.assertTrue(ne in list_)

    def test_extend_unique(self):
        # Test
        list_ = ErrorList()
        ne_1 = NodeError(1)
        ne_2 = NodeError(2)
        list_.extend([ne_1, ne_2, ne_1])
        # Verify
        self.assertEqual(len(list_), 2)
        self.assertTrue(ne_1 in list_)
        self.assertTrue(ne_2 in list_)

    def test_update(self):
        # Test
        list_ = ErrorList()
        ne_1 = NodeError(1, repo_id=None)
        ne_2 = NodeError(2, repo_id='repo_1')
        list_.update(repo_id='repo_2')
        # Verify
        for ne in list_:
            self.assertEqual(ne.details['repo_id'], 'repo_2')