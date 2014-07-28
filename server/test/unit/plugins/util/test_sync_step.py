import unittest

from mock import Mock

from pulp.plugins.util.sync_step import SyncStep, UnitSyncStep


class SyncStepTests(unittest.TestCase):

    def setUp(self):
        self.repo_id = 'publish-test-repo'
        self.mock_repo = Mock()
        self.mock_conduit = Mock()
        self.mock_conduit.get_repo_scratchpad = Mock(return_value={})
        self.mock_config = Mock()

    def test_get_conduit(self):
        syncer = SyncStep("base-step", repo=self.mock_repo, sync_conduit=self.mock_conduit,
                          config=self.mock_config, importer_type='test_importer_type')
        self.assertEquals(self.mock_conduit, syncer.get_conduit())

    def test_get_conduit_parent(self):
        syncer = SyncStep("base-step", repo=self.mock_repo, sync_conduit=None,
                          config=self.mock_config, importer_type='test_importer_type')
        parent_conduit = Mock()
        syncer.parent = Mock()
        syncer.parent.get_conduit.return_value = parent_conduit
        self.assertEquals(parent_conduit, syncer.get_conduit())

    def test_sync(self):
        syncer = SyncStep("base-step", repo=self.mock_repo, sync_conduit=self.mock_conduit,
                          config=self.mock_config, importer_type='test_importer_type')
        syncer.process_lifecycle = Mock()
        mock_report = Mock()
        syncer._build_final_report = Mock()
        syncer._build_final_report.return_value = mock_report
        retval = syncer.sync()
        syncer.process_lifecycle.assert_called_once()
        self.assertEquals(retval, mock_report)

    def test_init(self):
        syncer = SyncStep("base-step", repo=self.mock_repo, sync_conduit=self.mock_conduit,
                          config=self.mock_config, importer_type='test_importer_type')
        self.assertEquals(syncer.repo, self.mock_repo)
        self.assertEquals(syncer.sync_conduit, self.mock_conduit)
        self.assertEquals(syncer.config, self.mock_config)
        self.assertEquals(syncer.importer_type, 'test_importer_type')


class UnitSyncStepTests(unittest.TestCase):

    def test_init(self):
        unitsync = UnitSyncStep("foo-type", unit_type="baz", unit_fields="bar")
        self.assertEquals(unitsync.unit_type, ["baz"])
        self.assertTrue(isinstance(unitsync.skip_list, set))
        self.assertEquals(unitsync.unit_fields, "bar")

    def test_init_unit_type_list(self):
        unitsync = UnitSyncStep("foo-type", unit_type=["baz", "quux"], unit_fields="bar")
        self.assertEquals(unitsync.unit_type, ["baz", "quux"])
        self.assertTrue(isinstance(unitsync.skip_list, set))
        self.assertEquals(unitsync.unit_fields, "bar")

    def test_unit_generators(self):
        unitsync = UnitSyncStep("foo-type")
        try:
            unitsync.get_unit_generator()
            self.assertTrue(False, "exception not thrown")
        except NotImplementedError:
            pass
        except:
            self.assertTrue(False, "wrong exception thrown")

    def test_get_total(self):
        unitsync = UnitSyncStep("foo-type")
        try:
            unitsync._get_total()
            self.assertTrue(False, "exception not thrown")
        except NotImplementedError:
            pass
        except:
            self.assertTrue(False, "wrong exception thrown")
