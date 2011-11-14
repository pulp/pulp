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
import mock_plugins

import pulp.server.content.loader as plugin_loader
from pulp.server.db.model.gc_repository import Repo, RepoImporter
import pulp.server.managers.repo.cud as repo_manager
import pulp.server.managers.repo.importer as importer_manager

# -- test cases ---------------------------------------------------------------

class RepoManagerTests(testutil.PulpTest):

    def setUp(self):
        testutil.PulpTest.setUp(self)

        plugin_loader._create_loader()
        mock_plugins.install()

        # Create the manager instance to test
        self.repo_manager = repo_manager.RepoManager()
        self.importer_manager = importer_manager.RepoImporterManager()

    def tearDown(self):
        testutil.PulpTest.tearDown(self)
        mock_plugins.reset()

    def clean(self):
        testutil.PulpTest.clean(self)

        Repo.get_collection().remove()
        RepoImporter.get_collection().remove()
        
    def test_set_importer(self):
        """
        Tests setting an importer on a new repo (normal case).
        """

        # Setup
        self.repo_manager.create_repo('importer-test')
        importer_config = {'foo' : 'bar'}

        # Test
        self.importer_manager.set_importer('importer-test', 'mock-importer', importer_config)

        # Verify
        importer = RepoImporter.get_collection().find_one({'repo_id' : 'importer-test', 'id' : 'mock-importer'})
        self.assertEqual('importer-test', importer['repo_id'])
        self.assertEqual('mock-importer', importer['id'])
        self.assertEqual('mock-importer', importer['importer_type_id'])
        self.assertEqual(importer_config, importer['config'])

    def test_set_importer_no_repo(self):
        """
        Tests setting the importer on a repo that doesn't exist correctly
        informs the user.
        """

        # Test
        try:
            self.importer_manager.set_importer('fake', 'mock-importer', None)
        except repo_manager.MissingRepo, e:
            self.assertEqual(e.repo_id, 'fake')
            print(e) # for coverage

    def test_set_importer_no_importer(self):
        """
        Tests setting an importer that doesn't exist on a repo.
        """

        # Setup
        self.repo_manager.create_repo('real-repo')

        # Test
        try:
            self.importer_manager.set_importer('real-repo', 'fake-importer', None)
        except importer_manager.MissingImporter, e:
            self.assertEqual(e.importer_name, 'fake-importer')
            print(e) # for coverage

    def test_set_importer_with_existing(self):
        """
        Tests setting a different importer on a repo that already had one.
        """

        # Setup
        class MockImporter2:
            @classmethod
            def metadata(cls):
                return {'types': ['mock_types_2']}
            def validate_config(self, repo_data, importer_config):
                return True

        plugin_loader._LOADER.add_importer('MockImporter2', MockImporter2, {})

        self.repo_manager.create_repo('change_me')
        self.importer_manager.set_importer('change_me', 'mock-importer', None)

        # Test
        self.importer_manager.set_importer('change_me', 'MockImporter2', None)

        # Verify
        all_importers = list(RepoImporter.get_collection().find())
        self.assertEqual(1, len(all_importers))
        self.assertEqual(all_importers[0]['id'], 'MockImporter2')

    def test_set_importer_validate_raises_error(self):
        """
        Tests simulating an error coming out of the importer's validate config method.
        """

        # Setup
        mock_plugins.MOCK_IMPORTER.importer_added.side_effect = Exception()
        self.repo_manager.create_repo('repo-1')

        # Test
        config = {'hobbit' : 'frodo'}
        try:
            self.importer_manager.set_importer('repo-1', 'mock-importer', config)
            self.fail('Exception expected for importer plugin exception')
        except importer_manager.InvalidImporterConfiguration:
            pass

        # Cleanup
        mock_plugins.MOCK_IMPORTER.importer_added.side_effect = None

    def test_set_importer_invalid_config(self):
        """
        Tests the set_importer call properly errors when the config is invalid.
        """

        # Setup
        mock_plugins.MOCK_IMPORTER.validate_config.return_value = False
        self.repo_manager.create_repo('bad_config')

        # Test
        config = {'elf' : 'legolas'}
        try:
            self.importer_manager.set_importer('bad_config', 'mock-importer', config)
            self.fail('Exception expected for bad config')
        except importer_manager.InvalidImporterConfiguration:
            pass

    def test_get_set_importer_scratchpad(self):
        """
        Tests the retrieval and setting of a repo importer's scratchpad.
        """

        # Setup
        self.repo_manager.create_repo('repo')
        self.importer_manager.set_importer('repo', 'mock-importer', {})

        # Test - Unset Scratchpad
        scratchpad = self.importer_manager.get_importer_scratchpad('repo')
        self.assertTrue(scratchpad is None)

        # Test - Set
        contents = ['yendor', 'sokoban']
        self.importer_manager.set_importer_scratchpad('repo', contents)

        # Test - Get
        scratchpad = self.importer_manager.get_importer_scratchpad('repo')
        self.assertEqual(contents, scratchpad)

    def test_get_set_importer_scratchpad_missing(self):
        """
        Tests no error is raised when getting or setting the scratchpad for missing cases.
        """

        # Setup
        self.repo_manager.create_repo('empty')

        # Test - Get
        scratchpad = self.importer_manager.get_importer_scratchpad('empty')
        self.assertTrue(scratchpad is None)

        # Test - Set No Importer
        self.importer_manager.set_importer_scratchpad('empty', 'foo') # should not error

        # Test - Set Fake Repo
        self.importer_manager.set_importer_scratchpad('fake', 'bar') # should not error
