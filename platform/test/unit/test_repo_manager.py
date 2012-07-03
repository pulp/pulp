# -*- coding: utf-8 -*-
#
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

import os
import unittest

import base
import mock_plugins
import mock

from   pulp.common.util import encode_unicode
import pulp.plugins.loader as plugin_loader
from   pulp.server.db.model.repository import Repo, RepoImporter, RepoDistributor
import pulp.server.managers.repo.cud as repo_manager
import pulp.server.managers.factory as manager_factory
import pulp.server.managers.repo._common as common_utils
import pulp.server.exceptions as exceptions

# -- test cases ---------------------------------------------------------------

class RepoManagerTests(base.PulpServerTests):

    def setUp(self):
        super(RepoManagerTests, self).setUp()

        plugin_loader._create_loader()
        mock_plugins.install()

        # Create the manager instance to test
        self.manager = repo_manager.RepoManager()

    def tearDown(self):
        super(RepoManagerTests, self).tearDown()
        mock_plugins.reset()

    def clean(self):
        super(RepoManagerTests, self).clean()

        Repo.get_collection().remove()
        RepoImporter.get_collection().remove()
        RepoDistributor.get_collection().remove()

    def test_create(self):
        """
        Tests creating a repo with valid data is successful.
        """

        # Setup
        id = 'repo_1'
        name = 'Repository 1'
        description = 'Test Repository 1'
        notes = {'note1' : 'value1'}

        # Test
        created = self.manager.create_repo(id, name, description, notes)

        # Verify
        repos = list(Repo.get_collection().find())
        self.assertEqual(1, len(repos))

        repo = repos[0]
        self.assertEqual(id, repo['id'])
        self.assertEqual(name, repo['display_name'])
        self.assertEqual(description, repo['description'])
        self.assertEqual(notes, repo['notes'])

        self.assertEqual(id, created['id'])
        self.assertEqual(name, created['display_name'])
        self.assertEqual(description, created['description'])
        self.assertEqual(notes, created['notes'])

    def test_create_defaults(self):
        """
        Tests creating a repository with minimal information (ID) is successful.
        """

        # Test
        self.manager.create_repo('repo_1')

        # Verify
        repos = list(Repo.get_collection().find())
        self.assertEqual(1, len(repos))
        self.assertEqual('repo_1', repos[0]['id'])

        #   Assert the display name is defaulted to the id
        self.assertEqual('repo_1', repos[0]['display_name'])

    def _test_create_invalid_id(self):
        """
        Tests creating a repo with an invalid ID raises the correct error.
        """

        # Test
        try:
            self.manager.create_repo('bad id')
            self.fail('Invalid ID did not raise an exception')
        except exceptions.InvalidValue, e:
            self.assertTrue('bad id' in e)
            print(e) # for coverage

    def test_create_duplicate_id(self):
        """
        Tests creating a repo with an ID already being used by a repo raises
        the correct error.
        """

        # Setup
        id = 'duplicate'
        self.manager.create_repo(id)

        # Test
        try:
            self.manager.create_repo(id)
            self.fail('Repository with an existing ID did not raise an exception')
        except exceptions.DuplicateResource, e:
            self.assertTrue(id in e)
            print(e) # for coverage

    def test_create_invalid_notes(self):
        """
        Tests that creating a repo but passing a non-dict as the notes field
        raises the correct exception.
        """

        # Setup
        id = 'bad-notes'
        notes = 'not a dict'

        # Test
        try:
            self.manager.create_repo(id, notes=notes)
            self.fail('Invalid notes did not cause create to raise an exception')
        except exceptions.InvalidValue, e:
            self.assertTrue('notes' in e.data_dict()['property_names'])
            print(e) # for coverage

    def test_create_and_configure_repo(self):
        """
        Tests the successful creation of a repo + plugins.
        """

        # Setup
        repo_id = 'full'
        display_name = 'Full'
        description = 'Full Test'
        notes = {'n' : 'n'}
        importer_type_id = 'mock-importer'
        importer_repo_plugin_config = {'i' : 'i'}
        distributors = [
            ('mock-distributor', {'d' : 'd'}, True, 'dist1'),
            ('mock-distributor', {'d' : 'd'}, True, 'dist2')
        ]

        # Test
        created = self.manager.create_and_configure_repo(repo_id, display_name, description,
                  notes, importer_type_id, importer_repo_plugin_config, distributors)

        # Verify
        self.assertEqual(created['id'], repo_id)

        repo = Repo.get_collection().find_one({'id' : repo_id})
        self.assertEqual(repo['id'], repo_id)
        self.assertEqual(repo['display_name'], display_name)
        self.assertEqual(repo['description'], description)
        self.assertEqual(repo['notes'], notes)

        importer = RepoImporter.get_collection().find_one({'repo_id' : repo_id})
        self.assertEqual(importer['importer_type_id'], importer_type_id)
        self.assertEqual(importer['config'], importer_repo_plugin_config)

        for distributor_type, config, auto_publish, distributor_id in distributors:
            distributor = RepoDistributor.get_collection().find_one({'id' : distributor_id})
            self.assertEqual(distributor['repo_id'], repo_id)
            self.assertEqual(distributor['distributor_type_id'], distributor_type)
            self.assertEqual(distributor['auto_publish'], auto_publish)
            self.assertEqual(distributor['config'], config)

    def test_create_and_configure_repo_bad_importer(self):
        """
        Tests cleanup is successful when the add importer step fails.
        """

        # Setup
        mock_plugins.MOCK_IMPORTER.validate_config.return_value = False, ''

        # Test
        self.assertRaises(exceptions.PulpDataException, self.manager.create_and_configure_repo, 'repo-1', importer_type_id='mock-importer')

        # Verify the repo was deleted
        repo = Repo.get_collection().find_one({'id' : 'repo-1'})
        self.assertTrue(repo is None)

        # Cleanup
        mock_plugins.MOCK_IMPORTER.validate_config.return_value = True

    def test_create_and_configure_repo_bad_distributor(self):
        """
        Tests cleanup is successful when the add distributor step fails.
        """

        # Setup
        mock_plugins.MOCK_DISTRIBUTOR.validate_config.return_value = False, ''

        # Test
        distributors = [('mock-distributor', {}, True, None)]
        self.assertRaises(exceptions.PulpDataException, self.manager.create_and_configure_repo, 'repo-1', distributor_list=distributors)

        # Verify the repo was deleted
        repo = Repo.get_collection().find_one({'id' : 'repo-1'})
        self.assertTrue(repo is None)

        # Cleanup
        mock_plugins.MOCK_DISTRIBUTOR.validate_config.return_value = True

    def test_create_i18n(self):
        # Setup
        i18n_text = 'Brasília'

        # Test
        self.manager.create_repo('repo-i18n', display_name=i18n_text, description=i18n_text)

        # Verify
        repo = Repo.get_collection().find_one({'id' : 'repo-i18n'})
        self.assertTrue(repo is not None)
        self.assertEqual(encode_unicode(repo['display_name']), i18n_text)
        self.assertEqual(encode_unicode(repo['description']), i18n_text)

    def test_delete_repo(self):
        """
        Tests deleting a repo under normal circumstances.
        """

        # Setup
        id = 'doomed'
        self.manager.create_repo(id)

        # Test
        self.manager.delete_repo(id)

        # Verify
        repos = list(Repo.get_collection().find({'id' : id}))
        self.assertEqual(0, len(repos))

    def test_delete_repo_no_repo(self):
        """
        Tests that deleting a repo that doesn't exist raises the appropriate error.
        """

        # Test
        try:
            self.manager.delete_repo('fake repo')
            self.fail('Exception expected')
        except exceptions.MissingResource, e:
            self.assertTrue('fake repo' == e.resources['resource_id'])

    def test_delete_with_plugins(self):
        """
        Tests that deleting a repo that has importers and distributors configured deletes them as well.
        """

        # Setup
        self.manager.create_repo('doomed')

        importer_manager = manager_factory.repo_importer_manager()
        distributor_manager = manager_factory.repo_distributor_manager()

        importer_manager.set_importer('doomed', 'mock-importer', {})
        distributor_manager.add_distributor('doomed', 'mock-distributor', {}, True, distributor_id='dist-1')
        distributor_manager.add_distributor('doomed', 'mock-distributor', {}, True, distributor_id='dist-2')

        self.assertEqual(1, len(list(RepoImporter.get_collection().find({'repo_id' : 'doomed'}))))
        self.assertEqual(2, len(list(RepoDistributor.get_collection().find({'repo_id' : 'doomed'}))))

        # Test
        self.manager.delete_repo('doomed')

        # Verify
        self.assertEqual(0, len(list(Repo.get_collection().find())))

        self.assertEqual(0, len(list(RepoImporter.get_collection().find({'repo_id' : 'doomed'}))))
        self.assertEqual(0, len(list(RepoDistributor.get_collection().find({'repo_id' : 'doomed'}))))

        self.assertEqual(1, mock_plugins.MOCK_IMPORTER.importer_removed.call_count)
        self.assertEqual(2, mock_plugins.MOCK_DISTRIBUTOR.distributor_removed.call_count)

        repo_working_dir = common_utils.repository_working_dir('doomed', mkdir=False)
        self.assertTrue(not os.path.exists(repo_working_dir))
        
    def test_delete_with_plugin_error(self):
        """
        Tests deleting a repo where one (or more) of the plugins raises an error.
        """

        # Setup
        self.manager.create_repo('doomed')

        importer_manager = manager_factory.repo_importer_manager()
        distributor_manager = manager_factory.repo_distributor_manager()

        importer_manager.set_importer('doomed', 'mock-importer', {})
        distributor_manager.add_distributor('doomed', 'mock-distributor', {}, True, distributor_id='dist-1')

        #    Setup both mocks to raise errors on removal
        mock_plugins.MOCK_IMPORTER.importer_removed.side_effect = Exception('Splat')
        mock_plugins.MOCK_DISTRIBUTOR.distributor_removed.side_effect = Exception('Pow')

        # Test
        try:
            self.manager.delete_repo('doomed')
            self.fail('No exception raised during repo delete')
        except exceptions.PulpExecutionException, e:
            pass

        # Cleanup - need to manually clear the side effects
        mock_plugins.MOCK_IMPORTER.importer_removed.side_effect = None
        mock_plugins.MOCK_DISTRIBUTOR.distributor_removed.side_effect = None

    def test_update_repo(self):
        """
        Tests the case of successfully updating a repo.
        """

        # Setup
        self.manager.create_repo('update-me', display_name='display_name_1', description='description_1', notes={'a' : 'a', 'b' : 'b', 'c' : 'c'})

        delta = {
            'display_name' : 'display_name_2',
            'description'  : 'description_2',
            'notes'        : {'b' : 'x', 'c' : None},
            'disregard'    : 'ignored',
        }

        # Test
        updated = self.manager.update_repo('update-me', delta)

        # Verify
        expected_notes = {'a' : 'a', 'b' : 'x'}

        repo = Repo.get_collection().find_one({'id' : 'update-me'})
        self.assertEqual(repo['display_name'], delta['display_name'])
        self.assertEqual(repo['description'], delta['description'])
        self.assertEqual(repo['notes'], expected_notes)

        self.assertEqual(updated['display_name'], delta['display_name'])
        self.assertEqual(updated['description'], delta['description'])
        self.assertEqual(updated['notes'], expected_notes)

    def test_update_missing_repo(self):
        """
        Tests updating a repo that isn't there raises the appropriate exception.
        """

        # Test
        try:
            self.manager.update_repo('not-there', {})
            self.fail('Exception expected')
        except exceptions.MissingResource, e:
            self.assertTrue('not-there' == e.resources['resource_id'])

    def test_update_repo_and_plugins(self):
        """
        Tests the aggregate call to update a repo and its plugins.
        """

        # Setup
        self.manager.create_repo('repo-1', 'Original', 'Original Description')

        importer_manager = manager_factory.repo_importer_manager()
        distributor_manager = manager_factory.repo_distributor_manager()

        importer_manager.set_importer('repo-1', 'mock-importer', {'key-i1': 'orig-1'})
        distributor_manager.add_distributor('repo-1', 'mock-distributor', {'key-d1' : 'orig-1'}, True, distributor_id='dist-1')
        distributor_manager.add_distributor('repo-1', 'mock-distributor', {'key-d2' : 'orig-2'}, True, distributor_id='dist-2')

        # Test
        repo_delta = {'display_name' : 'Updated'}
        new_importer_config = {'key-i1' : 'updated-1', 'key-i2' : 'new-1'}
        new_distributor_configs = {
            'dist-1' : {'key-d1' : 'updated-1'},
        } # only update one of the two distributors

        repo = self.manager.update_repo_and_plugins('repo-1', repo_delta, new_importer_config, new_distributor_configs)

        # Verify
        self.assertEqual(repo['id'], 'repo-1')
        self.assertEqual(repo['display_name'], 'Updated')
        self.assertEqual(repo['description'], 'Original Description')

        importer = importer_manager.get_importer('repo-1')
        self.assertEqual(importer['config'], new_importer_config)

        dist_1 = distributor_manager.get_distributor('repo-1', 'dist-1')
        self.assertEqual(dist_1['config'], new_distributor_configs['dist-1'])

        dist_2 = distributor_manager.get_distributor('repo-1', 'dist-2')
        self.assertEqual(dist_2['config'], {'key-d2' : 'orig-2'})

    def test_update_repo_and_plugins_partial(self):
        """
        Tests no errors are encountered when only updating some of the possible fields.
        """

        # Setup
        self.manager.create_repo('repo-1', 'Original', 'Original Description')

        importer_manager = manager_factory.repo_importer_manager()
        distributor_manager = manager_factory.repo_distributor_manager()

        importer_manager.set_importer('repo-1', 'mock-importer', {'key-i1': 'orig-1'})
        distributor_manager.add_distributor('repo-1', 'mock-distributor', {'key-d1' : 'orig-1'}, True, distributor_id='dist-1')

        # Test
        repo = self.manager.update_repo_and_plugins('repo-1', None, None, None)

        # Verify
        self.assertEqual(repo['display_name'], 'Original')

        importer = importer_manager.get_importer('repo-1')
        self.assertEqual(importer['config'], {'key-i1' : 'orig-1'})

        dist_1 = distributor_manager.get_distributor('repo-1', 'dist-1')
        self.assertEqual(dist_1['config'], {'key-d1' : 'orig-1'})

    def test_get_set_scratchpad(self):
        """
        Tests retrieving and setting a repository's scratchpad.
        """

        # Setup
        repo_id = 'scratch-test'
        self.manager.create_repo(repo_id)

        # Test - get default
        value = self.manager.get_repo_scratchpad(repo_id)
        self.assertEqual({}, value)

        # Test - set
        new_value = {'i' : 'importer', 'd' : 'distributor'}
        self.manager.set_repo_scratchpad(repo_id, new_value)

        value = self.manager.get_repo_scratchpad(repo_id)
        self.assertEqual(new_value, value)

    def test_get_set_scratchpad_missing_repo(self):
        """
        Tests scratchpad calls for a repo that doesn't exist.
        """
        self.assertRaises(exceptions.MissingResource, self.manager.get_repo_scratchpad, 'foo')
        self.assertRaises(exceptions.MissingResource, self.manager.set_repo_scratchpad, 'foo', 'bar')

    def test_update_unit_count_missing_repo(self):
        self.assertRaises(exceptions.PulpExecutionException,
            self.manager.update_unit_count, 'foo', '2')

    @mock.patch.object(Repo, 'get_collection')
    def test_update_unit_count(self, mock_get_collection):
        mock_update = mock.MagicMock()
        mock_get_collection.return_value.update = mock_update

        ARGS = ('repo-123', 7)
        EXPECT = ({'id': 'repo-123'}, {'$inc': {'content_unit_count': 7}})

        self.manager.update_unit_count(*ARGS)
        #mock_update.assert_called_once_with(*EXPECT, safe=True)
        # if the data passed to mock is a var in this case the test fails.. weird..
        mock_update.assert_called_once_with({'id': 'repo-123'}, {'$inc': {'content_unit_count': 7}}, safe=True)

    def test_update_unit_count_with_db(self):
        """
        This test interacts with the database to ensure that the call to
        "update" uses valid syntax as interpreted by mongo and has the effect
        we expect.
        """
        REPO_ID = 'repo-123'
        # create repo, verify count of 0
        self.manager.create_repo(REPO_ID)
        repo = Repo.get_collection().find_one({'id' : REPO_ID})
        self.assertEqual(repo['content_unit_count'], 0)

        # increase unit count, verify result
        self.manager.update_unit_count(REPO_ID, 3)
        repo = Repo.get_collection().find_one({'id' : REPO_ID})
        self.assertEqual(repo['content_unit_count'], 3)


class UtilityMethodsTests(unittest.TestCase):

    def test_is_repo_id_valid(self):
        """
        Tests the repo ID validation with both valid and invalid IDs.
        """

        # Test
        self.assertTrue(repo_manager.is_repo_id_valid('repo'))
        self.assertTrue(repo_manager.is_repo_id_valid('repo1'))
        self.assertTrue(repo_manager.is_repo_id_valid('repo-1'))
        self.assertTrue(repo_manager.is_repo_id_valid('repo_1'))
        self.assertTrue(repo_manager.is_repo_id_valid('_repo'))

        self.assertTrue(not repo_manager.is_repo_id_valid('repo 1'))
        self.assertTrue(not repo_manager.is_repo_id_valid('repo#1'))
        self.assertTrue(not repo_manager.is_repo_id_valid('repo!'))
