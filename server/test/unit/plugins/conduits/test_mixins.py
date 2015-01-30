import mock

from ... import base
from pulp.devel import mock_plugins
from pulp.plugins.conduits.mixins import ImporterScratchPadMixin, ImporterConduitException
from pulp.server.db.model.repository import Repo
from pulp.server.managers.repo.cud import RepoManager
from pulp.server.managers.repo.importer import RepoImporterManager
import pulp.plugins.types.database as types_database
import pulp.server.managers.factory as manager_factory


class ImporterScratchPadMixinTests(base.PulpServerTests):

    def clean(self):
        super(ImporterScratchPadMixinTests, self).clean()
        types_database.clean()

        Repo.get_collection().remove()

    def setUp(self):
        super(ImporterScratchPadMixinTests, self).setUp()
        mock_plugins.install()

        self.repo_manager = RepoManager()
        self.importer_manager = RepoImporterManager()

        self.repo_id = 'repo-1'
        self.repo_manager.create_repo(self.repo_id)
        self.conduit = ImporterScratchPadMixin(self.repo_id, 'test-importer')

    def tearDown(self):
        super(ImporterScratchPadMixinTests, self).tearDown()
        manager_factory.reset()
        mock_plugins.reset()

    def test_get_set_scratchpad(self):
        """
        Tests scratchpad calls.
        """

        # Setup
        self.importer_manager.set_importer(self.repo_id, 'mock-importer', {})

        # Test - get no scratchpad
        self.assertTrue(self.conduit.get_scratchpad() is None)

        # Test - set scrathpad
        value = 'dragon'
        self.conduit.set_scratchpad(value)

        # Test - get updated value
        self.assertEqual(value, self.conduit.get_scratchpad())

    def test_scratchpad_with_error(self):
        # Setup
        mock_manager = mock.Mock()
        mock_manager.get_importer_scratchpad.side_effect = Exception()
        mock_manager.set_importer_scratchpad.side_effect = Exception()

        manager_factory._INSTANCES[manager_factory.TYPE_REPO_IMPORTER] = mock_manager

        # Test
        self.assertRaises(ImporterConduitException, self.conduit.get_scratchpad)
        self.assertRaises(ImporterConduitException, self.conduit.set_scratchpad, 'foo')
