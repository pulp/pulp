from unittest import TestCase

from pulp_node import error


class TestNodeError(TestCase):

    def test_constructor(self):
        # Test
        ne = error.NodeError(1, a=1, b=2)
        # Verify
        self.assertEqual(ne.error_id, 1)
        self.assertEqual(ne.details['a'], 1)
        self.assertEqual(ne.details['b'], 2)

    def test_equals(self):
        # Test
        ne_1 = error.NodeError(1, a=1, b=2)
        ne_2 = error.NodeError(1, a=1, b=2)
        ne_3 = error.NodeError(1, a=1, b=20)
        ne_4 = error.NodeError(2, a=1, b=2)
        # Verify
        self.assertEqual(ne_1, ne_2)
        self.assertNotEqual(ne_1, ne_3)
        self.assertNotEqual(ne_2, ne_4)

    def test_to_dict(self):
        # Test
        ne = error.NodeError(1, a=1, b=2)
        d = ne.dict()
        # Verify
        self.assertEqual(ne.error_id, d['error_id'])
        self.assertEqual(ne.details, d['details'])

    def test_load(self):
        # Test
        d = dict(error_id=1, details=dict(a=1, b=2))
        ne = error.NodeError(None)
        ne.load(d)
        # Verify
        self.assertEqual(ne.error_id, 1)
        self.assertEqual(ne.details, dict(a=1, b=2))

    def test_load_failed(self):
        ne = error.NodeError(None)

        self.assertRaises(ValueError, ne.load, [])


class TestErrors(TestCase):

    def test_caught_exception(self):
        # Test
        exception = ValueError('must be integer')
        ne = error.CaughtException(exception, repo_id='repo_1')
        # Verify
        self.assertEqual(ne.error_id, error.CaughtException.ERROR_ID)
        self.assertEqual(ne.details['message'], str(exception))
        self.assertEqual(ne.details['repo_id'], 'repo_1')
        self.assertTrue(isinstance(str(ne), str))

    def test_purge_orphans(self):
        # Test
        ne = error.PurgeOrphansError(http_code=401)
        # Verify
        self.assertEqual(ne.error_id, error.PurgeOrphansError.ERROR_ID)
        self.assertEqual(ne.details['http_code'], 401)
        self.assertTrue(isinstance(str(ne), str))

    def test_repo_sync(self):
        # Test
        ne = error.RepoSyncRestError(repo_id='repo_1', http_code=401)
        # Verify
        self.assertEqual(ne.error_id, error.RepoSyncRestError.ERROR_ID)
        self.assertEqual(ne.details['http_code'], 401)
        self.assertEqual(ne.details['repo_id'], 'repo_1')
        self.assertTrue(isinstance(str(ne), str))

    def test_get_bindings(self):
        # Test
        ne = error.GetBindingsError(http_code=401)
        # Verify
        self.assertEqual(ne.error_id, error.GetBindingsError.ERROR_ID)
        self.assertEqual(ne.details['http_code'], 401)
        self.assertTrue(isinstance(str(ne), str))

    def test_get_child_units(self):
        # Test
        ne = error.GetChildUnitsError(repo_id='repo_1')
        # Verify
        self.assertEqual(ne.error_id, error.GetChildUnitsError.ERROR_ID)
        self.assertEqual(ne.details['repo_id'], 'repo_1')
        self.assertTrue(isinstance(str(ne), str))

    def test_get_parent_units(self):
        # Test
        ne = error.GetParentUnitsError(repo_id='repo_1')
        # Verify
        self.assertEqual(ne.error_id, error.GetParentUnitsError.ERROR_ID)
        self.assertEqual(ne.details['repo_id'], 'repo_1')
        self.assertTrue(isinstance(str(ne), str))

    def test_importer_not_installed(self):
        # Test
        ne = error.ImporterNotInstalled(repo_id='repo_1', type_id='abc')
        # Verify
        self.assertEqual(ne.error_id, error.ImporterNotInstalled.ERROR_ID)
        self.assertEqual(ne.details['repo_id'], 'repo_1')
        self.assertEqual(ne.details['type_id'], 'abc')
        self.assertTrue(isinstance(str(ne), str))

    def test_distributor_not_installed(self):
        # Test
        ne = error.DistributorNotInstalled(repo_id='repo_1', type_id='abc')
        # Verify
        self.assertEqual(ne.error_id, error.DistributorNotInstalled.ERROR_ID)
        self.assertEqual(ne.details['repo_id'], 'repo_1')
        self.assertEqual(ne.details['type_id'], 'abc')
        self.assertTrue(isinstance(str(ne), str))

    def test_manifest_download(self):
        # Test
        url = 'http://redhat.com/manifest'
        ne = error.ManifestDownloadError(url, message='abc')
        # Verify
        self.assertEqual(ne.error_id, error.ManifestDownloadError.ERROR_ID)
        self.assertEqual(ne.details['url'], url)
        self.assertEqual(ne.details['message'], 'abc')
        self.assertTrue(isinstance(str(ne), str))

    def test_unit_download(self):
        # Test
        url = 'http://redhat.com/unit_1'
        ne = error.UnitDownloadError(url, repo_id='repo_1', message='abc')
        # Verify
        self.assertEqual(ne.error_id, error.UnitDownloadError.ERROR_ID)
        self.assertEqual(ne.details['url'], url)
        self.assertEqual(ne.details['repo_id'], 'repo_1')
        self.assertEqual(ne.details['message'], 'abc')
        self.assertTrue(isinstance(str(ne), str))

    def test_add_unit(self):
        # Test
        ne = error.AddUnitError(repo_id='repo_1')
        # Verify
        self.assertEqual(ne.error_id, error.AddUnitError.ERROR_ID)
        self.assertEqual(ne.details['repo_id'], 'repo_1')
        self.assertTrue(isinstance(str(ne), str))

    def test_delete_unit(self):
        # Test
        ne = error.DeleteUnitError(repo_id='repo_1')
        # Verify
        self.assertEqual(ne.error_id, error.DeleteUnitError.ERROR_ID)
        self.assertEqual(ne.details['repo_id'], 'repo_1')
        self.assertTrue(isinstance(str(ne), str))

    def test_invalid_manifest(self):
        # Test
        ne = error.InvalidManifestError()
        # Verify
        self.assertEqual(ne.error_id, error.InvalidManifestError.ERROR_ID)


class TestErrorList(TestCase):

    def test_append(self):
        # Test
        list_ = error.ErrorList()
        ne_1 = error.NodeError(1)
        ne_2 = error.NodeError(2)
        list_.append(ne_1)
        list_.append(ne_2)
        # Verify
        self.assertEqual(len(list_), 2)
        self.assertTrue(ne_1 in list_)
        self.assertTrue(ne_2 in list_)

    def test_unique_append(self):
        # Test
        list_ = error.ErrorList()
        ne_1 = error.NodeError(1)
        ne_2 = error.NodeError(2)
        list_.append(ne_1)
        list_.append(ne_2)
        list_.append(ne_2)
        # Verify
        self.assertEqual(len(list_), 2)
        self.assertTrue(ne_1 in list_)
        self.assertTrue(ne_2 in list_)

    def test_append_value_error(self):
        # Test
        list_ = error.ErrorList()
        self.assertRaises(ValueError, list_.append, 1)
        # Verify
        self.assertEqual(len(list_), 0)

    def test_extend(self):
        # Test
        list_ = error.ErrorList()
        ne = error.NodeError(1)
        list_.extend([ne])
        # Verify
        self.assertEqual(len(list_), 1)
        self.assertTrue(ne in list_)

    def test_extend_unique(self):
        # Test
        list_ = error.ErrorList()
        ne_1 = error.NodeError(1)
        ne_2 = error.NodeError(2)
        list_.extend([ne_1, ne_2, ne_1])
        # Verify
        self.assertEqual(len(list_), 2)
        self.assertTrue(ne_1 in list_)
        self.assertTrue(ne_2 in list_)

    def test_update(self):
        # Test
        list_ = error.ErrorList()
        error.NodeError(1, repo_id=None)
        error.NodeError(2, repo_id='repo_1')
        list_.update(repo_id='repo_2')
        # Verify
        for ne in list_:
            self.assertEqual(ne.details['repo_id'], 'repo_2')
