import mock

from .... import base
from pulp.devel import mock_plugins
from pulp.plugins.loader import api as plugins
from pulp.server.db import model
from pulp.server.db.model.consumer import (Bind, Consumer, RepoProfileApplicability,
                                           UnitProfile)
from pulp.server.db.model.criteria import Criteria
from pulp.server.db.model.repository import RepoDistributor
from pulp.server.managers import factory as factory
from pulp.server.managers.consumer.applicability import (
    _add_consumers_to_applicability_map, _add_profiles_to_consumer_map_and_get_hashes,
    _add_repo_ids_to_consumer_map, _format_report, _get_applicability_map,
    _get_consumer_applicability_map, DoesNotExist, MultipleObjectsReturned,
    retrieve_consumer_applicability, ApplicabilityRegenerationManager)
from pulp.server.managers.consumer.bind import BindManager
from pulp.server.managers.consumer.cud import ConsumerManager
from pulp.server.managers.consumer.profile import ProfileManager


class ApplicabilityRegenerationManagerTests(base.PulpServerTests):

    CONSUMER_IDS = ['consumer-1', 'consumer-2']
    FILTER = {'id': {'$in': CONSUMER_IDS}}
    SORT = [{'id': 1}]
    CONSUMER_CRITERIA = Criteria(filters=FILTER, sort=SORT).as_dict()
    PROFILE1 = [{'name': 'zsh', 'version': '1.0'}, {'name': 'ksh', 'version': '1.0'}]
    PROFILE2 = [{'name': 'zsh', 'version': '2.0'}, {'name': 'ksh', 'version': '2.0'}]
    REPO_IDS = ['repo-1', 'repo-2']
    REPO_CRITERIA = Criteria(filters={'id': {'$in': REPO_IDS}}, sort=[{'id': 1}])
    YUM_DISTRIBUTOR_ID = 'yum_distributor'

    def setUp(self):
        base.PulpServerTests.setUp(self)
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        Consumer.get_collection().remove()
        UnitProfile.get_collection().remove()
        RepoProfileApplicability.get_collection().remove()
        plugins._create_manager()
        mock_plugins.install()

        yum_profiler, cfg = plugins.get_profiler_by_type('rpm')
        yum_profiler.calculate_applicable_units = \
            mock.Mock(side_effect=lambda p, r, c, x:
                      {'rpm': ['rpm-1', 'rpm-2'],
                       'erratum': ['errata-1', 'errata-2']})

        yum_profiler.metadata = mock.Mock(return_value={'types': ['rpm', 'erratum']})

        self.old_get_existing = ApplicabilityRegenerationManager._get_existing_repo_content_types
        ApplicabilityRegenerationManager._get_existing_repo_content_types = mock.Mock(
            return_value=['rpm', 'erratum'])

    def tearDown(self):
        base.PulpServerTests.tearDown(self)
        model.Repository.drop_collection()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        Consumer.get_collection().remove()
        UnitProfile.get_collection().remove()
        RepoProfileApplicability.get_collection().remove()
        mock_plugins.reset()
        ApplicabilityRegenerationManager._get_existing_repo_content_types = staticmethod(
            self.old_get_existing)

    def populate_consumers(self):
        # Register consumers with rpm profiles
        manager = factory.consumer_manager()
        for id in self.CONSUMER_IDS:
            manager.register(id)
        manager = factory.consumer_profile_manager()
        for id in self.CONSUMER_IDS:
            manager.create(id, 'rpm', self.PROFILE1)

    def populate_consumers_different_profiles(self):
        # Register consumers with rpm profiles
        manager = factory.consumer_manager()
        for id in self.CONSUMER_IDS:
            manager.register(id)
        manager = factory.consumer_profile_manager()
        manager.create(self.CONSUMER_IDS[0], 'rpm', self.PROFILE1)
        manager.create(self.CONSUMER_IDS[1], 'rpm', self.PROFILE2)

    def populate_repos(self):
        distributor_manager = factory.repo_distributor_manager()
        # Create repos and add distributor
        for repo_id in self.REPO_IDS:
            distributor_manager.add_distributor(repo_id, 'mock-distributor', {}, True,
                                                self.YUM_DISTRIBUTOR_ID)

    def populate_bindings(self):
        self.populate_repos()
        bind_manager = factory.consumer_bind_manager()
        # Add bindings for the given repos and consumers
        for consumer_id in self.CONSUMER_IDS:
            for repo_id in self.REPO_IDS:
                bind_manager.bind(consumer_id, repo_id, self.YUM_DISTRIBUTOR_ID, False, {})

    # Applicability regeneration for consumers with no unit profiles associated with them
    @mock.patch('pulp.server.managers.consumer.bind.model.Repository.objects')
    def test_regenerate_applicability_for_consumers_with_no_profiles(self, mock_repo_qs):
        # Setup
        manager = factory.consumer_manager()
        for consumer_id in self.CONSUMER_IDS:
            manager.register(consumer_id)
        # Test without bindings
        manager = factory.applicability_regeneration_manager()
        manager.regenerate_applicability_for_consumers(self.CONSUMER_CRITERIA)
        applicability_list = list(RepoProfileApplicability.get_collection().find())
        self.assertEqual(len(applicability_list), 0)
        # Test with bindings
        self.populate_bindings()
        manager.regenerate_applicability_for_consumers(self.CONSUMER_CRITERIA)
        applicability_list = list(RepoProfileApplicability.get_collection().find())
        self.assertEqual(len(applicability_list), 0)

    # Applicability regeneration with consumer criteria
    @mock.patch('pulp.server.managers.consumer.bind.model.Repository.objects')
    def test_regenerate_applicability_for_consumers_with_different_profiles(self, mock_repo_qs):
        self.populate_consumers_different_profiles()
        self.populate_bindings()
        manager = factory.applicability_regeneration_manager()
        manager.regenerate_applicability_for_consumers(self.CONSUMER_CRITERIA)
        # Verify
        applicability_list = list(RepoProfileApplicability.get_collection().find())
        self.assertEqual(len(applicability_list), 4)
        expected_applicability = {'rpm': ['rpm-1', 'rpm-2'], 'erratum': ['errata-1', u'errata-2']}
        for applicability in applicability_list:
            self.assertEqual(applicability['applicability'], expected_applicability)
            self.assertTrue(applicability['profile'] in [self.PROFILE1, self.PROFILE2])

    @mock.patch('pulp.server.managers.consumer.bind.model.Repository.objects')
    def test_regenerate_applicability_for_consumers_with_same_profiles(self, mock_repo_qs):
        self.populate_consumers()
        self.populate_bindings()
        manager = factory.applicability_regeneration_manager()
        manager.regenerate_applicability_for_consumers(self.CONSUMER_CRITERIA)
        # Verify
        applicability_list = list(RepoProfileApplicability.get_collection().find())
        self.assertEqual(len(applicability_list), 2)
        expected_applicability = {'rpm': ['rpm-1', 'rpm-2'], 'erratum': ['errata-1', u'errata-2']}
        for applicability in applicability_list:
            self.assertEqual(applicability['profile'], self.PROFILE1)
            self.assertEqual(applicability['applicability'], expected_applicability)

    @mock.patch('pulp.server.managers.consumer.bind.model.Repository.objects')
    def test_regenerate_applicability_for_empty_consumer_criteria(self, mock_repo_qs):
        self.populate_consumers()
        self.populate_bindings()
        manager = factory.applicability_regeneration_manager()
        manager.regenerate_applicability_for_consumers(Criteria())
        # Verify
        applicability_list = list(RepoProfileApplicability.get_collection().find())
        self.assertEqual(len(applicability_list), 2)
        expected_applicability = {'rpm': ['rpm-1', 'rpm-2'], 'erratum': ['errata-1', u'errata-2']}
        for applicability in applicability_list:
            self.assertEqual(applicability['profile'], self.PROFILE1)
            self.assertEqual(applicability['applicability'], expected_applicability)

    def test_regenerate_applicability_for_consumer_criteria_no_bindings(self):
        # Setup
        self.populate_consumers()
        # Test
        manager = factory.applicability_regeneration_manager()
        manager.regenerate_applicability_for_consumers(self.CONSUMER_CRITERIA)
        # Verify
        applicability_list = list(RepoProfileApplicability.get_collection().find())
        self.assertEqual(applicability_list, [])

    @mock.patch('pulp.server.managers.consumer.bind.model.Repository.objects')
    def test_regenerate_applicability_for_consumers_profiler_notfound(self, mock_repo_qs):
        self.populate_consumers()
        self.populate_bindings()
        profiler, cfg = plugins.get_profiler_by_type('rpm')
        profiler.calculate_applicable_units = mock.Mock(side_effect=NotImplementedError())
        manager = factory.applicability_regeneration_manager()
        manager.regenerate_applicability_for_consumers(self.CONSUMER_CRITERIA)
        # Verify
        applicability_list = list(RepoProfileApplicability.get_collection().find())
        self.assertEqual(len(applicability_list), 0)

    # Applicability regeneration with repo criteria
    @mock.patch('pulp.server.managers.consumer.bind.model.Repository.objects')
    def test_regenerate_applicability_for_repos_with_different_consumer_profiles(
            self, mock_repo_qs):
        self.populate_consumers_different_profiles()
        self.populate_bindings()
        manager = factory.applicability_regeneration_manager()
        manager.regenerate_applicability_for_consumers(self.CONSUMER_CRITERIA)
        manager.queue_regenerate_applicability_for_repos(self.REPO_CRITERIA)
        # Verify
        applicability_list = list(RepoProfileApplicability.get_collection().find())
        self.assertEqual(len(applicability_list), 4)
        expected_applicability = {'rpm': ['rpm-1', 'rpm-2'], 'erratum': ['errata-1', u'errata-2']}
        for applicability in applicability_list:
            self.assertEqual(applicability['applicability'], expected_applicability)
            self.assertTrue(applicability['profile'] in [self.PROFILE1, self.PROFILE2])

    @mock.patch('pulp.server.managers.consumer.bind.model.Repository.objects')
    def test_regenerate_applicability_for_repos_with_same_consumer_profiles(self, mock_repo_qs):
        self.populate_consumers()
        self.populate_bindings()
        manager = factory.applicability_regeneration_manager()
        manager.regenerate_applicability_for_consumers(self.CONSUMER_CRITERIA)
        manager.queue_regenerate_applicability_for_repos(self.REPO_CRITERIA)
        # Verify
        applicability_list = list(RepoProfileApplicability.get_collection().find())
        self.assertEqual(len(applicability_list), 2)
        expected_applicability = {'rpm': ['rpm-1', 'rpm-2'], 'erratum': ['errata-1', u'errata-2']}
        for applicability in applicability_list:
            self.assertEqual(applicability['profile'], self.PROFILE1)
            self.assertEqual(applicability['applicability'], expected_applicability)

    @mock.patch('pulp.server.managers.consumer.bind.model.Repository.objects')
    def test_regenerate_applicability_for_empty_repo_criteria(self, mock_repo_qs):
        self.populate_consumers()
        self.populate_bindings()
        manager = factory.applicability_regeneration_manager()
        manager.regenerate_applicability_for_consumers(self.CONSUMER_CRITERIA)
        manager.queue_regenerate_applicability_for_repos(Criteria())
        # Verify
        applicability_list = list(RepoProfileApplicability.get_collection().find())
        self.assertEqual(len(applicability_list), 2)
        expected_applicability = {'rpm': ['rpm-1', 'rpm-2'], 'erratum': ['errata-1', u'errata-2']}
        for applicability in applicability_list:
            self.assertEqual(applicability['profile'], self.PROFILE1)
            self.assertEqual(applicability['applicability'], expected_applicability)

    @mock.patch('pulp.server.managers.consumer.bind.model.Repository.objects')
    def test_regenerate_applicability_for_repo_criteria_no_bindings(self, mock_repo_qs):
        self.populate_repos()
        manager = factory.applicability_regeneration_manager()
        manager.queue_regenerate_applicability_for_repos(self.REPO_CRITERIA)
        # Verify
        applicability_list = list(RepoProfileApplicability.get_collection().find())
        self.assertEqual(applicability_list, [])

    @mock.patch('pulp.server.managers.consumer.bind.model.Repository.objects')
    def test_regenerate_applicability_for_repos_profiler_notfound(self, mock_repo_qs):
        self.populate_consumers()
        self.populate_bindings()
        profiler, cfg = plugins.get_profiler_by_type('rpm')
        profiler.calculate_applicable_units = mock.Mock(side_effect=NotImplementedError())
        # Test
        manager = factory.applicability_regeneration_manager()
        manager.queue_regenerate_applicability_for_repos(self.REPO_CRITERIA)
        # Verify
        applicability_list = list(RepoProfileApplicability.get_collection().find())
        self.assertEqual(len(applicability_list), 0)

    @mock.patch('pulp.server.managers.consumer.bind.model.Repository.objects')
    def test_regenerate_applicability_for_repos_consumer_profile_updated(self, mock_repo_qs):
        factory.consumer_manager().register(self.CONSUMER_IDS[0])
        factory.consumer_profile_manager().create(self.CONSUMER_IDS[0], 'rpm', self.PROFILE1)
        factory.repo_distributor_manager().add_distributor(self.REPO_IDS[0],
                                                           'mock-distributor',
                                                           {},
                                                           True,
                                                           self.YUM_DISTRIBUTOR_ID)
        factory.consumer_bind_manager().bind(self.CONSUMER_IDS[0],
                                             self.REPO_IDS[0],
                                             self.YUM_DISTRIBUTOR_ID,
                                             False,
                                             {})

        # Request applicability generation for the consumer
        applicability_manager = factory.applicability_regeneration_manager()
        applicability_manager.regenerate_applicability_for_consumers(self.CONSUMER_CRITERIA)
        # Update the consumer profile
        profile_manager = factory.consumer_profile_manager()
        profile_manager.update(self.CONSUMER_IDS[0], 'rpm', {'name': 'zsh', 'version': '1.0'})
        # Request applicability regeneration for the repo and assert that no exception is raised
        applicability_manager.queue_regenerate_applicability_for_repos(self.REPO_CRITERIA)

        applicability_list = list(RepoProfileApplicability.get_collection().find())
        self.assertEqual(len(applicability_list), 1)
        expected_applicability = {'rpm': ['rpm-1', 'rpm-2'], 'erratum': ['errata-1', 'errata-2']}
        self.assertEqual(applicability_list[0]['profile'], self.PROFILE1)
        self.assertEqual(applicability_list[0]['applicability'], expected_applicability)

    @mock.patch('pulp.server.managers.consumer.applicability.model.Repository.objects')
    @mock.patch('pulp.server.db.model.consumer.RepoProfileApplicability.get_collection')
    @mock.patch('pulp.server.db.model.consumer.UnitProfile.get_collection')
    def test_batch_regenerate_applicability(self, mock_unit_profile_get_collection,
                                            mock_repo_profile_app_get_collection, mock_repo_qs):

        factory.initialize()
        applicability_manager = ApplicabilityRegenerationManager()
        mock_repo = mock.MagicMock()
        mock_repo.repo_id = 'fake-repo'
        mock_repo_qs.find_by_criteria.return_value = [mock_repo]
        existing_ids = ({'_id': 'mock-object-id'}, {'_id': 'mock-object-id-2'})
        applicability_manager.batch_regenerate_applicability('mock_repo', existing_ids)

        # validate that batch size of 5 is used
        expected_params = {'_id': {'$in': ['mock-object-id', 'mock-object-id-2']}}
        mock_repo_profile_app_get_collection.return_value.find.assert_called_with(expected_params)

    @mock.patch('pulp.server.managers.consumer.applicability.model.Repository.objects')
    def test_get_existing_repo_content_types_no_repo(self, mock_repo_qs):
        """
        Test that if a repository does not exist, return an empty list.

        This set up isn't ideal, but the class setUp mocks this function.
        """
        mock_repo_qs.first.return_value = None
        content_types = self.old_get_existing('repo')
        self.assertEqual(content_types, [])

    @mock.patch('pulp.server.managers.consumer.applicability.model.Repository.objects')
    def test_get_existing_repo_content_types_repo_no_units(self, mock_repo_qs):
        """
        Test that if a repository exists but has no units, return an empty list.
        """
        mock_repo = mock_repo_qs.first.return_value
        mock_repo.content_unit_counts = {'mock_type': 0}
        content_types = self.old_get_existing('repo')
        self.assertEqual(content_types, [])

    @mock.patch('pulp.server.managers.consumer.applicability.model.Repository.objects')
    def test_get_existing_repo_content_types_repo_units(self, mock_repo_qs):
        """
        Test that if a repository exists but has no units, return an empty list.
        """
        mock_repo = mock_repo_qs.get.return_value
        mock_repo.content_unit_counts = {'mock_type_1': 4, 'mock_type_2': 8}
        content_types = self.old_get_existing('repo')
        self.assertListEqual(content_types, ['mock_type_2', 'mock_type_1'])


class TestRepoProfileApplicabilityManager(base.PulpServerTests):
    """
    Test the RepoProfileApplicabilityManager.
    """
    def setUp(self):
        """
        Store the collection on self.
        """
        super(TestRepoProfileApplicabilityManager, self).setUp()
        mock_plugins.install()
        self.collection = RepoProfileApplicability.get_collection()

    def tearDown(self):
        """
        Clean up the collection.
        """
        super(TestRepoProfileApplicabilityManager, self).tearDown()
        self.collection.drop()
        model.Repository.drop_collection()
        Consumer.get_collection().drop()
        UnitProfile.get_collection().drop()
        mock_plugins.reset()

    def test_create(self):
        """
        Test the create() method.
        """
        profile_hash = 'hash'
        repo_id = 'repo_id'
        profile = ['a', 'profile']
        applicability_data = {'type_id': ['package a', 'package c']}
        # At this point, there should be nothing in the database
        self.assertEqual(self.collection.find().count(), 0)

        # Saving the model should store it in the database
        applicability = RepoProfileApplicability.objects.create(
            profile_hash=profile_hash, repo_id=repo_id, profile=profile,
            applicability=applicability_data)

        # There should now be one entry in the DB
        self.assertEqual(self.collection.find().count(), 1)
        document = self.collection.find_one()
        self.assertEqual(document['profile_hash'], profile_hash)
        self.assertEqual(document['repo_id'], repo_id)
        self.assertEqual(document['profile'], profile)
        self.assertEqual(document['applicability'], applicability_data)

        # Our applicability object should now have the correct _id attribute
        self.assertEqual(applicability._id, document['_id'])

    def test_filter(self):
        """
        Test the filter() method.
        """
        # Let's create three objects, and filter for two of them
        a_1 = RepoProfileApplicability.objects.create(
            profile_hash='hash_1', repo_id='repo_1', profile='profile',
            applicability='applicability')
        a_2 = RepoProfileApplicability.objects.create(
            profile_hash='hash_2', repo_id='repo_1', profile='profile',
            applicability='applicability')
        RepoProfileApplicability.objects.create(
            profile_hash='hash_1', repo_id='repo_2', profile='profile',
            applicability='applicability')

        applicabilities = RepoProfileApplicability.objects.filter({'repo_id': 'repo_1'})

        # We should have gotten a_1 and a_2
        self.assertEqual(len(applicabilities), 2)
        self.assertEqual(set([a._id for a in applicabilities]), set([a_1._id, a_2._id]))
        # Make sure the objects were instantiated correctly
        for a in applicabilities:
            if a['_id'] == a_1._id:
                expected = a_1
            else:
                expected = a_2
            self.assertEqual(a['profile_hash'], expected.profile_hash)
            self.assertEqual(a['repo_id'], expected.repo_id)
            self.assertEqual(a['profile'], expected.profile)
            self.assertEqual(a['applicability'], expected.applicability)

    def test_filter_nothing(self):
        """
        Assert that queries that don't match anything are OK
        """
        self.assertEqual(RepoProfileApplicability.objects.filter({'repo_id': 'no_repo'}),
                         [])

    def test_get(self):
        """
        Test the get() method.
        """
        # Let's create three objects, and get one of them
        RepoProfileApplicability.objects.create(
            profile_hash='hash_1', repo_id='repo_1', profile='profile',
            applicability='applicability')
        a_2 = RepoProfileApplicability.objects.create(
            profile_hash='hash_2', repo_id='repo_1', profile='profile',
            applicability='applicability')
        RepoProfileApplicability.objects.create(
            profile_hash='hash_1', repo_id='repo_2', profile='profile',
            applicability='applicability')

        applicability = RepoProfileApplicability.objects.get(
            {'repo_id': 'repo_1', 'profile_hash': 'hash_2'})

        # We should have gotten a_2
        self.assertEqual(applicability._id, a_2._id)
        # Make sure the object was instantiated correctly
        self.assertEqual(applicability['profile_hash'], a_2.profile_hash)
        self.assertEqual(applicability['repo_id'], a_2.repo_id)
        self.assertEqual(applicability['profile'], a_2.profile)
        self.assertEqual(applicability['applicability'], a_2.applicability)

    def test_get_matches_more_than_one(self):
        """
        Test the get() method, when it matches more than one object.
        """
        # Let's create three objects, and get all of them
        RepoProfileApplicability.objects.create(
            profile_hash='hash_1', repo_id='repo_1', profile='profile',
            applicability='applicability')
        RepoProfileApplicability.objects.create(
            profile_hash='hash_2', repo_id='repo_1', profile='profile',
            applicability='applicability')
        RepoProfileApplicability.objects.create(
            profile_hash='hash_1', repo_id='repo_2', profile='profile',
            applicability='applicability')

        self.assertRaises(MultipleObjectsReturned,
                          RepoProfileApplicability.objects.get, {})

    def test_get_matches_none(self):
        """
        Test the get() method, when it matches no object.
        """
        self.assertRaises(DoesNotExist,
                          RepoProfileApplicability.objects.get, {})

    @mock.patch('pulp.server.managers.consumer.applicability.model.Repository.objects')
    def test_remove_orphans(self, mock_repo_qs):
        """
        Test the remove_orphans() method with various cases
        """
        # Create a RepoProfileApplicability object that references an existing repo and profile.
        repo = {'id': 'a_repo_id'}
        mock_repo_qs.distinct.return_value = [repo['id']]
        consumer, certificate = ConsumerManager().register('consumer_id')
        profile_1 = ProfileManager().create(consumer.id, 'content_type', 'profile_data')
        profile_2 = ProfileManager().create(consumer.id, 'other_content_type', 'more_profile_data')
        # This one should remain
        rpa_1 = RepoProfileApplicability.objects.create(profile_1.profile_hash, 'a_repo_id',
                                                        profile_1.profile, 'applicability_data')
        # This one should be removed, because it references a profile_hash that doesn't exist
        RepoProfileApplicability.objects.create('profile_hash_doesnt_exist', 'a_repo_id',
                                                profile_1.profile, 'applicability_data')
        # This one should be removed, because it references a repo_id that doesn't exist
        RepoProfileApplicability.objects.create(
            profile_1.profile_hash, 'repo_doesnt_exist', profile_1.profile, 'applicability_data_2')
        # This one should also remain
        rpa_4 = RepoProfileApplicability.objects.create(profile_2.profile_hash, 'a_repo_id',
                                                        profile_2.profile, 'applicability_data')
        # There should be four rpas
        self.assertEqual(len(RepoProfileApplicability.objects.filter({})), 4)

        # Order the RPAs to be cleaned
        RepoProfileApplicability.objects.remove_orphans()

        # rpa_2 and rpa_3 should have been removed
        self.assertEqual(len(RepoProfileApplicability.objects.filter({})), 2)
        existing_rpas = RepoProfileApplicability.objects.filter({})
        existing_rpa_ids = [rpa._id for rpa in existing_rpas]
        self.assertEqual(set(existing_rpa_ids), set([rpa_1._id, rpa_4._id]))

    @mock.patch('pulp.server.managers.consumer.applicability.model.Repository.objects')
    def test_remove_orphans_missing_profile_hash(self, mock_repo_qs):
        """
        Test the remove_orphans() method with a non-existing profile_hash
        """
        # Create a RepoProfileApplicability object that references an existing repo and profile.
        repo = {'id': 'a_repo_id'}
        mock_repo_qs.distinct.return_value = [repo['id']]
        consumer, certificate = ConsumerManager().register('consumer_id')
        profile = ProfileManager().create(consumer.id, 'content_type', 'profile_data')
        rpa_1 = RepoProfileApplicability.objects.create(profile.profile_hash, 'a_repo_id',
                                                        profile.profile, 'applicability_data')
        # This one should be removed, because it references a profile_hash that doesn't exist
        RepoProfileApplicability.objects.create('profile_hash_doesnt_exist', 'a_repo_id',
                                                profile.profile, 'applicability_data')
        # There should be two rpas
        self.assertEqual(len(RepoProfileApplicability.objects.filter({})), 2)

        # Order the RPAs to be cleaned
        RepoProfileApplicability.objects.remove_orphans()

        # rpa_2 should have been removed
        self.assertEqual(len(RepoProfileApplicability.objects.filter({})), 1)
        existing_rpa = RepoProfileApplicability.objects.get({})
        self.assertEqual(rpa_1._id, existing_rpa._id)

    @mock.patch('pulp.server.managers.consumer.applicability.model.Repository.objects')
    def test_remove_orphans_missing_repo(self, mock_repo_qs):
        """
        Test the remove_orphans() method with a non-existing repo_id
        """
        # Create a RepoProfileApplicability object that references an existing repo and profile.
        repo = {'id': 'a_repo_id'}
        mock_repo_qs.distinct.return_value = [repo['id']]
        consumer, certificate = ConsumerManager().register('consumer_id')
        profile = ProfileManager().create(consumer.id, 'content_type', 'profile_data')
        rpa_1 = RepoProfileApplicability.objects.create(profile.profile_hash, repo['id'],
                                                        profile.profile, 'applicability_data')
        # This one should be removed, because it references a repo_id that doesn't exist
        RepoProfileApplicability.objects.create(profile.profile_hash, 'repo_doesnt_exist',
                                                profile.profile, 'applicability_data_2')
        # There should be two rpas
        self.assertEqual(len(RepoProfileApplicability.objects.filter({})), 2)

        # Order the RPAs to be cleaned
        RepoProfileApplicability.objects.remove_orphans()

        # rpa_2 should have been removed
        self.assertEqual(len(RepoProfileApplicability.objects.filter({})), 1)
        existing_rpa = RepoProfileApplicability.objects.get({})
        self.assertEqual(rpa_1._id, existing_rpa._id)

    @mock.patch('pulp.server.managers.consumer.applicability.model.Repository.objects')
    def test_remove_orphans_nothing_to_remove(self, mock_repo_qs):
        """
        Test the remove_orphans() method, when there is nothing to remove.
        """
        # Create a RepoProfileApplicability object that references an existing repo and profile.
        repo = {'id': 'a_repo_id'}
        mock_repo_qs.distinct.return_value = [repo['id']]
        consumer, certificate = ConsumerManager().register('consumer_id')
        profile = ProfileManager().create(consumer.id, 'content_type', 'profile_data')
        rpa = RepoProfileApplicability.objects.create(profile.profile_hash, repo['id'],
                                                      profile.profile, 'applicability_data')
        # The new rpa should be the only one
        self.assertEqual(len(RepoProfileApplicability.objects.filter({})), 1)

        # Order the RPAs to be cleaned
        RepoProfileApplicability.objects.remove_orphans()

        # Nothing should have been removed
        self.assertEqual(len(RepoProfileApplicability.objects.filter({})), 1)
        existing_rpa = RepoProfileApplicability.objects.get({})
        self.assertEqual(rpa._id, existing_rpa._id)


class TestRetrieveConsumerApplicability(base.PulpServerTests,
                                        base.RecursiveUnorderedListComparisonMixin):
    """
    Test the retrieve_consumer_applicability() function.
    """
    def tearDown(self):
        """
        Empty the collections that were written to during this test suite.
        """
        super(TestRetrieveConsumerApplicability, self).tearDown()
        Consumer.get_collection().remove()
        UnitProfile.get_collection().remove()
        RepoProfileApplicability.get_collection().drop()
        Bind.get_collection().drop()

    @mock.patch('pulp.server.managers.consumer.bind.factory.consumer_history_manager')
    @mock.patch('pulp.server.managers.consumer.bind.factory.repo_distributor_manager')
    @mock.patch('pulp.server.managers.consumer.bind.model.Repository.objects')
    def test_consumers_with_same_applicability(self, *unused_mocks):
        """
        Test that we can handle consumers that share applicability correctly.
        """
        # Set up the consumers
        consumer_ids = ['consumer_1', 'consumer_2']
        manager = factory.consumer_manager()
        for consumer_id in consumer_ids:
            manager.register(consumer_id)
        # In order for the consumers to have the same applicability, they will need the
        # same profile, so we'll just make one
        consumer_profile_data = ['unit_1-0.9.1', 'unit_2-1.1.3', 'unit_3-12.0.13']
        manager = ProfileManager()
        for consumer_id in consumer_ids:
            consumer_profile = manager.create(consumer_id, 'content_type',
                                              consumer_profile_data)
        # Create our precalcaulated applicability object
        applicability = {'content_type': ['unit_1-0.9.2', 'unit_3-13.0.1']}
        RepoProfileApplicability.objects.create(consumer_profile.profile_hash, 'repo_id',
                                                consumer_profile_data, applicability)
        # Create repository bindings to put them on the same repos
        bind_manager = BindManager()
        for consumer_id in consumer_ids:
            bind_manager.bind(consumer_id, 'repo_id', 'distributor_id', False, {})
        criteria = Criteria(filters={})

        applicability = retrieve_consumer_applicability(criteria)

        expected_applicability = [
            {'consumers': ['consumer_1', 'consumer_2'],
             'applicability': {'content_type': ['unit_1-0.9.2', 'unit_3-13.0.1']}}]
        self.assert_equal_ignoring_list_order(applicability, expected_applicability)

    @mock.patch('pulp.server.managers.consumer.bind.factory.consumer_history_manager')
    @mock.patch('pulp.server.managers.consumer.bind.factory.repo_distributor_manager')
    @mock.patch('pulp.server.managers.consumer.bind.model.Repository.objects')
    def test_disparate_consumers(self, *unused_mocks):
        """
        Test that the function handles two consumers with different
        applicability data correctly.
        """
        # Set up the consumers
        consumer_ids = ['consumer_1', 'consumer_2']
        manager = factory.consumer_manager()
        for consumer_id in consumer_ids:
            manager.register(consumer_id)
        # Set up consumer profile data
        consumer_profiles = {
            'consumer_1': [{'type': 'content_type_1', 'profile': ['unit_4-1.9']}],
            'consumer_2': [{'type': 'content_type_1',
                            'profile': ['unit_1-0.9.1', 'unit_2-1.1.3',
                                        'unit_3-12.0.13']}]}
        manager = ProfileManager()
        profile_map = {}
        for consumer_id, profiles in consumer_profiles.items():
            profile_map[consumer_id] = []
            for profile in profiles:
                consumer_profile = manager.create(consumer_id, profile['type'],
                                                  profile['profile'])
                profile_map[consumer_id].append(
                    {'hash': consumer_profile.profile_hash,
                     'profile': consumer_profile.profile})
        # Create our precalcaulated applicability objects
        applicabilities = [
            # Consumer_2's applicability
            {'profile_hash': profile_map['consumer_2'][0]['hash'],
             'profile': profile_map['consumer_2'][0]['profile'],
             'repo_id': 'repo_2',
             'applicability': {'content_type_1': ['unit_3-13.1.0']}},
            # Consumer_1's applicability
            {'profile_hash': profile_map['consumer_1'][0]['hash'],
             'profile': profile_map['consumer_1'][0]['profile'],
             'repo_id': 'repo_1',
             'applicability': {'content_type_1': ['unit_1-0.9.2', 'unit_3-13.0.1']}}]
        for a in applicabilities:
            RepoProfileApplicability.objects.create(a['profile_hash'], a['repo_id'],
                                                    a['profile'], a['applicability'])
        # Create repository bindings
        bind_manager = BindManager()
        bind_manager.bind('consumer_1', 'repo_1', 'distributor_id', False, {})
        bind_manager.bind('consumer_2', 'repo_2', 'distributor_id', False, {})
        criteria = Criteria(filters={})

        applicability = retrieve_consumer_applicability(criteria)

        expected_applicability = [
            {'consumers': ['consumer_1'],
             'applicability': {'content_type_1': ['unit_1-0.9.2', 'unit_3-13.0.1']}},
            {'consumers': ['consumer_2'],
             'applicability': {'content_type_1': ['unit_3-13.1.0']}}]
        self.assert_equal_ignoring_list_order(applicability, expected_applicability)

    @mock.patch('pulp.server.managers.consumer.bind.factory.consumer_history_manager')
    @mock.patch('pulp.server.managers.consumer.bind.factory.repo_distributor_manager')
    @mock.patch('pulp.server.managers.consumer.bind.model.Repository.objects')
    def test_empty_type_limiting(self, *unused_mocks):
        """
        Test with an empty list as the type limiting criteria.
        """
        # Set up the consumers
        consumer_ids = ['consumer_1', 'consumer_2']
        manager = factory.consumer_manager()
        for consumer_id in consumer_ids:
            manager.register(consumer_id)
        # Set up consumer profile data
        consumer_profiles = {
            'consumer_1': [{'type': 'content_type_1', 'profile': ['unit_4-1.9']},
                           {'type': 'content_type_2',
                            'profile': ['unit_1-0.9.1', 'unit_2-1.1.3',
                                        'unit_3-12.0.13']}],
            'consumer_2': [{'type': 'content_type_2',
                            'profile': ['unit_1-0.8.7', 'unit_2-1.1.3',
                                        'unit_3-12.0.13']}]}
        manager = ProfileManager()
        profile_map = {}
        for consumer_id, profiles in consumer_profiles.items():
            for profile in profiles:
                consumer_profile = manager.create(consumer_id, profile['type'],
                                                  profile['profile'])
                profile_map[consumer_profile.content_type] = \
                    {'hash': consumer_profile.profile_hash,
                     'profile': consumer_profile.profile}
        # Create our precalcaulated applicability objects
        applicabilities = [
            {'profile_hash': profile_map['content_type_1']['hash'],
             'profile': profile_map['content_type_1']['profile'],
             'repo_id': 'repo_1',
             'applicability': {'content_type_1': ['unit_4-1.9.1']}},
            {'profile_hash': profile_map['content_type_2']['hash'],
             'profile': profile_map['content_type_2']['profile'],
             'repo_id': 'repo_2',
             'applicability': {'content_type_1': ['unit_4-1.9.3'],
                               'content_type_2': ['unit_1-0.9.2', 'unit_3-13.0.1']}},
            {'profile_hash': profile_map['content_type_2']['hash'],
             'profile': profile_map['content_type_2']['profile'],
             'repo_id': 'repo_3',
             'applicability': {'content_type_2': ['unit_3-13.1.0']}}]
        for a in applicabilities:
            RepoProfileApplicability.objects.create(a['profile_hash'], a['repo_id'],
                                                    a['profile'], a['applicability'])
        # Create repository bindings
        bind_manager = BindManager()
        # Consumer 1 is bound to repo 1 and 2
        bind_manager.bind('consumer_1', 'repo_1', 'distributor_id', False, {})
        bind_manager.bind('consumer_1', 'repo_2', 'distributor_id', False, {})
        # Consumer 2 is bound to repo 2 and 3
        bind_manager.bind('consumer_2', 'repo_2', 'distributor_id', False, {})
        bind_manager.bind('consumer_2', 'repo_3', 'distributor_id', False, {})
        criteria = Criteria(filters={})

        # The content_types below is the empty list, so nothing should come back
        applicability = retrieve_consumer_applicability(criteria, content_types=[])

        # We told it not to give us any content types, so it should be empty
        self.assertEqual(applicability, [])

    @mock.patch('pulp.server.managers.consumer.bind.factory.consumer_history_manager')
    @mock.patch('pulp.server.managers.consumer.bind.factory.repo_distributor_manager')
    @mock.patch('pulp.server.managers.consumer.bind.model.Repository.objects')
    def test_limit_by_type(self, *unused_mocks):
        """
        Test that we allow the caller to limit applicability data by unit type.
        """
        # Set up the consumers
        consumer_ids = ['consumer_1', 'consumer_2']
        manager = factory.consumer_manager()
        for consumer_id in consumer_ids:
            manager.register(consumer_id)
        # Set up consumer profile data
        consumer_profiles = {
            'consumer_1': [{'type': 'content_type_1', 'profile': ['unit_4-1.9']},
                           {'type': 'content_type_2',
                            'profile': ['unit_1-0.9.1', 'unit_2-1.1.3',
                                        'unit_3-12.0.13']}],
            'consumer_2': [{'type': 'content_type_2',
                            'profile': ['unit_1-0.9.1', 'unit_2-1.1.3',
                                        'unit_3-12.0.13']}]}
        manager = ProfileManager()
        profile_map = {}
        for consumer_id, profiles in consumer_profiles.items():
            for profile in profiles:
                consumer_profile = manager.create(consumer_id, profile['type'],
                                                  profile['profile'])
                profile_map[consumer_profile.content_type] = \
                    {'hash': consumer_profile.profile_hash,
                     'profile': consumer_profile.profile}
        # Create our precalcaulated applicability objects
        applicabilities = [
            # This one should not appear in the output since content_type_1 is excluded
            {'profile_hash': profile_map['content_type_1']['hash'],
             'profile': profile_map['content_type_1']['profile'],
             'repo_id': 'repo_1',
             'applicability': {'content_type_1': ['unit_4-1.9.1']}},
            # The content_type_2 applicability data should be included in the output for
            # consumer_1 and consumer_2
            {'profile_hash': profile_map['content_type_2']['hash'],
             'profile': profile_map['content_type_2']['profile'],
             'repo_id': 'repo_2',
             'applicability': {'content_type_1': ['unit_4-1.9.3'],
                               'content_type_2': ['unit_1-0.9.2', 'unit_3-13.0.1']}},
            # Only consumer_2 is bound to repo_3, so this unit_3 should apply to only it
            {'profile_hash': profile_map['content_type_2']['hash'],
             'profile': profile_map['content_type_2']['profile'],
             'repo_id': 'repo_3',
             'applicability': {'content_type_2': ['unit_3-13.1.0']}}]
        for a in applicabilities:
            RepoProfileApplicability.objects.create(a['profile_hash'], a['repo_id'],
                                                    a['profile'], a['applicability'])
        # Create repository bindings
        bind_manager = BindManager()
        # Consumer 1 is bound to repo 1 and 2
        bind_manager.bind('consumer_1', 'repo_1', 'distributor_id', False, {})
        bind_manager.bind('consumer_1', 'repo_2', 'distributor_id', False, {})
        # Consumer 2 is bound to repo 2 and 3 (so it should get an additional unit_3)
        bind_manager.bind('consumer_2', 'repo_2', 'distributor_id', False, {})
        bind_manager.bind('consumer_2', 'repo_3', 'distributor_id', False, {})
        criteria = Criteria(filters={})

        # Pass in that we are only interested in content_type_2
        applicability = retrieve_consumer_applicability(criteria, ['content_type_2'])

        # We should get the criteria for the single content type back
        expected_applicability = [
            {'consumers': ['consumer_1', 'consumer_2'],
             'applicability': {'content_type_2': ['unit_1-0.9.2', 'unit_3-13.0.1']}},
            {'consumers': ['consumer_2'],
             'applicability': {
                 'content_type_2': ['unit_3-13.1.0']}}]
        self.assert_equal_ignoring_list_order(applicability, expected_applicability)

    @mock.patch('pulp.server.managers.consumer.bind.factory.consumer_history_manager')
    @mock.patch('pulp.server.managers.consumer.bind.factory.repo_distributor_manager')
    @mock.patch('pulp.server.managers.consumer.bind.model.Repository.objects')
    def test_mixed_case(self, *unused_mocks):
        """
        Make sure the function can handle a mixed case of consumers.
        """
        # Set up the consumers
        consumer_ids = ['consumer_1', 'consumer_2', 'consumer_3']
        manager = factory.consumer_manager()
        for consumer_id in consumer_ids:
            manager.register(consumer_id)
        # Set up consumer profile data
        consumer_profiles = {
            'consumer_1': [{'type': 'content_type_1',
                            'profile': ['unit_1-0.9.1', 'unit_3-12.9.3']}],
            'consumer_2': [{'type': 'content_type_1',
                            'profile': ['unit_1-0.9.1', 'unit_3-12.9.3']},
                           {'type': 'content_type_2',
                            'profile': ['unit_3-12.9.0']}],
            'consumer_3': [{'type': 'content_type_1',
                            'profile': ['unit_2-2.0.13']}]}
        manager = ProfileManager()
        profile_map = {}
        for consumer_id, profiles in consumer_profiles.items():
            profile_map[consumer_id] = []
            for profile in profiles:
                consumer_profile = manager.create(consumer_id, profile['type'],
                                                  profile['profile'])
                profile_map[consumer_id].append(
                    {'hash': consumer_profile.profile_hash,
                     'profile': consumer_profile.profile})
        # Create our precalcaulated applicability objects
        applicabilities = [
            # consumer_1 and 2's applicability
            {'profile_hash': profile_map['consumer_1'][0]['hash'],
             'profile': profile_map['consumer_1'][0]['profile'],
             'repo_id': 'repo_1',
             'applicability': {'content_type_1': ['unit_1-0.9.2', 'unit_3-13.0.1']}},
            # Consumer_2's applicability
            {'profile_hash': profile_map['consumer_2'][1]['hash'],
             'profile': profile_map['consumer_2'][1]['profile'],
             'repo_id': 'repo_2',
             'applicability': {'content_type_2': ['unit_3-13.1.0']}},
            # Consumer_3's applicability
            {'profile_hash': profile_map['consumer_3'][0]['hash'],
             'profile': profile_map['consumer_3'][0]['profile'],
             'repo_id': 'repo_1',
             'applicability': {'content_type_1': ['unit_2-3.1.1']}}]
        for a in applicabilities:
            RepoProfileApplicability.objects.create(a['profile_hash'], a['repo_id'],
                                                    a['profile'], a['applicability'])
        # Create repository bindings
        bind_manager = BindManager()
        bind_manager.bind('consumer_1', 'repo_1', 'distributor_id', False, {})
        # Consumer_2 is bound to repo_1 and repo_2. It's binding to repo_2 gets it another
        # applicability
        bind_manager.bind('consumer_2', 'repo_1', 'distributor_id', False, {})
        bind_manager.bind('consumer_2', 'repo_2', 'distributor_id', False, {})
        bind_manager.bind('consumer_3', 'repo_1', 'distributor_id', False, {})
        criteria = Criteria(filters={})

        applicability = retrieve_consumer_applicability(criteria)

        expected_applicability = [
            {'consumers': ['consumer_1', 'consumer_2'],
             'applicability': {'content_type_1': ['unit_1-0.9.2', 'unit_3-13.0.1']}},
            {'consumers': ['consumer_2'],
             'applicability': {'content_type_2': ['unit_3-13.1.0']}},
            {'consumers': ['consumer_3'],
             'applicability': {'content_type_1': ['unit_2-3.1.1']}}]
        self.assert_equal_ignoring_list_order(applicability, expected_applicability)

    @mock.patch('pulp.server.managers.consumer.bind.factory.consumer_history_manager')
    @mock.patch('pulp.server.managers.consumer.bind.factory.repo_distributor_manager')
    @mock.patch('pulp.server.managers.consumer.bind.model.Repository.objects')
    def test_multiple_applicability_data_matches(self, *unused_mocks):
        """
        Test that the function properly handles the case when multiple
        applicability objects map to a consumer. They should get aggregated and not
        clobber each other.
        """
        # Set up the consumers
        consumer_ids = ['consumer_1']
        manager = factory.consumer_manager()
        for consumer_id in consumer_ids:
            manager.register(consumer_id)
        # Set up consumer profile data
        consumer_profiles = {
            'consumer_1': [{'type': 'content_type_1',
                            'profile': ['unit_1-0.9.1', 'unit_3-12.9.3']}]}
        manager = ProfileManager()
        profile_map = {}
        for consumer_id, profiles in consumer_profiles.items():
            profile_map[consumer_id] = []
            for profile in profiles:
                consumer_profile = manager.create(consumer_id, profile['type'],
                                                  profile['profile'])
                profile_map[consumer_id].append(
                    {'hash': consumer_profile.profile_hash,
                     'profile': consumer_profile.profile})
        # Create our precalcaulated applicability objects
        applicabilities = [
            # consumer_1's applicability from repo_1
            {'profile_hash': profile_map['consumer_1'][0]['hash'],
             'profile': profile_map['consumer_1'][0]['profile'],
             'repo_id': 'repo_1',
             'applicability': {'content_type_1': ['unit_1-0.9.2', 'unit_3-13.0.1']}},
            # Consumer_1's applicability from repo_2
            {'profile_hash': profile_map['consumer_1'][0]['hash'],
             'profile': profile_map['consumer_1'][0]['profile'],
             'repo_id': 'repo_2',
             'applicability': {'content_type_1': ['unit_3-13.1.0']}}]
        for a in applicabilities:
            RepoProfileApplicability.objects.create(a['profile_hash'], a['repo_id'],
                                                    a['profile'], a['applicability'])
        # Create repository bindings
        bind_manager = BindManager()
        bind_manager.bind('consumer_1', 'repo_1', 'distributor_id', False, {})
        bind_manager.bind('consumer_1', 'repo_2', 'distributor_id', False, {})
        criteria = Criteria(filters={})

        applicability = retrieve_consumer_applicability(criteria)

        # We should get the criteria for the single consumer back
        expected_applicability = [
            {'consumers': ['consumer_1'],
             'applicability': {
                 'content_type_1': ['unit_1-0.9.2', 'unit_3-13.0.1', 'unit_3-13.1.0']}}]
        self.assert_equal_ignoring_list_order(applicability, expected_applicability)

    @mock.patch('pulp.server.managers.consumer.bind.factory.consumer_history_manager')
    @mock.patch('pulp.server.managers.consumer.bind.factory.repo_distributor_manager')
    @mock.patch('pulp.server.managers.consumer.bind.model.Repository.objects')
    def test_non_matching_consumer_ids(self, *unused_mocks):
        """
        Test the function when the given consumer_ids do not match any
        consumers.
        """
        # Set up the consumers
        consumer_ids = ['consumer_1']
        manager = factory.consumer_manager()
        for consumer_id in consumer_ids:
            manager.register(consumer_id)
        # Set up consumer profile data
        consumer_profiles = {
            'consumer_1': [{'type': 'content_type_1',
                            'profile': ['unit_1-0.9.1', 'unit_3-12.9.3']}]}
        manager = ProfileManager()
        profile_map = {}
        for consumer_id, profiles in consumer_profiles.items():
            profile_map[consumer_id] = []
            for profile in profiles:
                consumer_profile = manager.create(consumer_id, profile['type'],
                                                  profile['profile'])
                profile_map[consumer_id].append(
                    {'hash': consumer_profile.profile_hash,
                     'profile': consumer_profile.profile})
        # Create our precalcaulated applicability objects
        applicabilities = [
            # consumer_1's applicability from repo_1
            {'profile_hash': profile_map['consumer_1'][0]['hash'],
             'profile': profile_map['consumer_1'][0]['profile'],
             'repo_id': 'repo_1',
             'applicability': {'content_type_1': ['unit_1-0.9.2', 'unit_3-13.0.1']}},
            # Consumer_1's applicability from repo_2
            {'profile_hash': profile_map['consumer_1'][0]['hash'],
             'profile': profile_map['consumer_1'][0]['profile'],
             'repo_id': 'repo_2',
             'applicability': {'content_type_1': ['unit_3-13.1.0']}}]
        for a in applicabilities:
            RepoProfileApplicability.objects.create(a['profile_hash'], a['repo_id'],
                                                    a['profile'], a['applicability'])
        # Create repository bindings
        bind_manager = BindManager()
        bind_manager.bind('consumer_1', 'repo_1', 'distributor_id', False, {})
        bind_manager.bind('consumer_1', 'repo_2', 'distributor_id', False, {})
        criteria = Criteria(filters={'id': 'does_not_exist'})

        applicability = retrieve_consumer_applicability(criteria)

        # We should get no applicability back
        self.assert_equal_ignoring_list_order(applicability, [])

    @mock.patch('pulp.server.managers.consumer.bind.factory.consumer_history_manager')
    @mock.patch('pulp.server.managers.consumer.bind.factory.repo_distributor_manager')
    @mock.patch('pulp.server.managers.consumer.bind.model.Repository.objects')
    def test_single_consumer(self, *unused_mocks):
        """
        Test that the function handles matching a single consumer correctly.
        """
        # Set up the consumers
        consumer_ids = ['consumer_1', 'consumer_2', 'consumer_3']
        manager = factory.consumer_manager()
        for consumer_id in consumer_ids:
            manager.register(consumer_id)
        # Set up consumer profile data
        consumer_profiles = {
            'consumer_1': [{'type': 'content_type_1',
                            'profile': ['unit_1-0.9.1', 'unit_3-12.9.3']}],
            'consumer_2': [{'type': 'content_type_1',
                            'profile': ['unit_1-0.9.1', 'unit_3-12.9.3']},
                           {'type': 'content_type_2',
                            'profile': ['unit_3-12.9.0']}],
            'consumer_3': [{'type': 'content_type_1',
                            'profile': ['unit_2-2.0.13']}]}
        manager = ProfileManager()
        profile_map = {}
        for consumer_id, profiles in consumer_profiles.items():
            profile_map[consumer_id] = []
            for profile in profiles:
                consumer_profile = manager.create(consumer_id, profile['type'],
                                                  profile['profile'])
                profile_map[consumer_id].append(
                    {'hash': consumer_profile.profile_hash,
                     'profile': consumer_profile.profile})
        # Create our precalcaulated applicability objects
        applicabilities = [
            # consumer_1 and 2's applicability
            {'profile_hash': profile_map['consumer_1'][0]['hash'],
             'profile': profile_map['consumer_1'][0]['profile'],
             'repo_id': 'repo_1',
             'applicability': {'content_type_1': ['unit_1-0.9.2', 'unit_3-13.0.1']}},
            # Consumer_2's applicability
            {'profile_hash': profile_map['consumer_2'][1]['hash'],
             'profile': profile_map['consumer_2'][1]['profile'],
             'repo_id': 'repo_2',
             'applicability': {'content_type_2': ['unit_3-13.1.0']}},
            # Consumer_3's applicability
            {'profile_hash': profile_map['consumer_3'][0]['hash'],
             'profile': profile_map['consumer_3'][0]['profile'],
             'repo_id': 'repo_1',
             'applicability': {'content_type_1': ['unit_2-3.1.1']}}]
        for a in applicabilities:
            RepoProfileApplicability.objects.create(a['profile_hash'], a['repo_id'],
                                                    a['profile'], a['applicability'])
        # Create repository bindings
        bind_manager = BindManager()
        bind_manager.bind('consumer_1', 'repo_1', 'distributor_id', False, {})
        # Consumer_2 is bound to repo_1 and repo_2. It's binding to repo_2 gets it another
        # applicability
        bind_manager.bind('consumer_2', 'repo_1', 'distributor_id', False, {})
        bind_manager.bind('consumer_2', 'repo_2', 'distributor_id', False, {})
        bind_manager.bind('consumer_3', 'repo_1', 'distributor_id', False, {})
        criteria = Criteria(filters={'id': 'consumer_2'})

        applicability = retrieve_consumer_applicability(criteria)

        # We should get the criteria for the single consumer back
        expected_applicability = [
            {'consumers': ['consumer_2'],
             'applicability': {'content_type_1': ['unit_1-0.9.2', 'unit_3-13.0.1'],
                               'content_type_2': ['unit_3-13.1.0']}}]
        self.assert_equal_ignoring_list_order(applicability, expected_applicability)


class TestAddConsumersToApplicabilityMap(base.PulpServerTests,
                                         base.RecursiveUnorderedListComparisonMixin):
    """
    Test the _add_consumer_to_applicability_map() function.
    """
    def test__add_consumers_to_applicability_map(self):
        """
        Test the _add_consumers_to_applicability_map() function.
        """
        consumer_map = {
            'consumer_1': {'profiles': [{'profile_hash': 'hash_1'},
                                        {'profile_hash': 'hash_2'}],
                           'repo_ids': ['repo_1']},
            'consumer_2': {'profiles': [{'profile_hash': 'hash_2'},
                                        {'profile_hash': 'hash_3'}],
                           'repo_ids': ['repo_1', 'repo_2']},
            'consumer_3': {'profiles': [{'profile_hash': 'hash_1'},
                                        {'profile_hash': 'hash_4'}],
                           'repo_ids': ['repo_3']},
        }
        # The applicability_map should be altered by _add_consumers_to_applicability_map()
        # by having the consumers in the consumer_map added to the correct applicability
        # spots. The applicability_map doesn't have data for every combo of profile and
        # repo, so that we can make sure the function is able to handle that case
        # gracefully.
        applicability_map = {
            ('hash_1', 'repo_1'): {'consumers': [], 'applicability': ['a_1']},
            ('hash_2', 'repo_1'): {'consumers': [], 'applicability': ['a_2']},
            ('hash_2', 'repo_2'): {'consumers': [], 'applicability': ['a_3']},
            # This one should not match any consumers
            ('hash_5', 'repo_3'): {'consumers': [], 'applicability': ['a_4']},
        }

        _add_consumers_to_applicability_map(consumer_map, applicability_map)

        expected_applicability_map = {
            ('hash_1', 'repo_1'): {'consumers': ['consumer_1'],
                                   'applicability': ['a_1']},
            ('hash_2', 'repo_1'): {'consumers': ['consumer_1', 'consumer_2'],
                                   'applicability': ['a_2']},
            ('hash_2', 'repo_2'): {'consumers': ['consumer_2'],
                                   'applicability': ['a_3']},
            ('hash_5', 'repo_3'): {'consumers': [], 'applicability': ['a_4']},
        }
        self.assert_equal_ignoring_list_order(applicability_map,
                                              expected_applicability_map)


class TestAddProfilesToConsumerMapAndGetHashes(
        base.PulpServerTests, base.RecursiveUnorderedListComparisonMixin):
    """
    Test the _add_profiles_to_consumer_map_and_get_hashes() function.
    """
    def tearDown(self):
        """
        Empty the collections that were written to during this test suite.
        """
        super(TestAddProfilesToConsumerMapAndGetHashes, self).tearDown()
        Consumer.get_collection().remove()
        UnitProfile.get_collection().remove()

    def test__add_profiles_to_consumer_map_and_get_hashes(self):
        """
        Test the _add_profiles_to_consumer_map_and_get_hashes() function.
        """
        # Set up the consumers
        consumer_ids = ['consumer_1', 'consumer_2']
        manager = factory.consumer_manager()
        for consumer_id in consumer_ids:
            manager.register(consumer_id)
        # Set up consumer profile data
        consumer_profiles = {
            'consumer_1': [{'type': 'content_type_1',
                            'profile': ['unit_1-0.9.1', 'unit_3-12.9.3']},
                           {'type': 'content_type_2',
                            'profile': 'a_profile'}],
            'consumer_2': [{'type': 'content_type_2', 'profile': 'a_profile'}]}
        manager = ProfileManager()
        profile_map = {}
        expected_hashes = set()
        for consumer_id, profiles in consumer_profiles.items():
            profile_map[consumer_id] = []
            for profile in profiles:
                consumer_profile = manager.create(consumer_id, profile['type'],
                                                  profile['profile'])
                profile_map[consumer_id].append(
                    {'hash': consumer_profile.profile_hash,
                     'profile': consumer_profile.profile})
                expected_hashes.add(consumer_profile.profile_hash)
        expected_hashes = list(expected_hashes)
        consumer_map = {
            'consumer_1': {'profiles': []},
            'consumer_2': {'profiles': []}
        }

        hashes = _add_profiles_to_consumer_map_and_get_hashes(
            consumer_ids, consumer_map)

        self.assertEqual(set(consumer_map.keys()), set(['consumer_1', 'consumer_2']))
        self.assertEqual(len(consumer_map['consumer_1']['profiles']), 2)
        self.assertEqual(len(consumer_map['consumer_2']['profiles']), 1)
        self.assertEqual(set([p['profile_hash']
                              for p in consumer_map['consumer_1']['profiles']]),
                         set([profile_map['consumer_1'][0]['hash'],
                              profile_map['consumer_1'][1]['hash']]))
        self.assertEqual(consumer_map['consumer_2']['profiles'][0]['profile_hash'],
                         profile_map['consumer_2'][0]['hash'])
        # _add_profiles_to_consumer_map_and_get_hashes should return a list of unique
        # hashes, and this test only creates two unique hashes
        self.assertEqual(len(hashes), 2)
        self.assert_equal_ignoring_list_order(hashes, expected_hashes)


class TestAddRepoIDsToConsumerMap(base.PulpServerTests,
                                  base.RecursiveUnorderedListComparisonMixin):
    """
    Test the _add_repo_ids_to_consumer_map() function.
    """
    def tearDown(self):
        """
        Empty the collections that were written to during this test suite.
        """
        super(TestAddRepoIDsToConsumerMap, self).tearDown()
        Consumer.get_collection().remove()
        Bind.get_collection().remove()

    # We mock this because we don't care about consumer history in this test suite, and it
    # saves some DB access time and cleanup
    @mock.patch('pulp.server.managers.consumer.bind.factory.consumer_history_manager')
    # By mocking these, we can avoid having to create repos and distributors for this test
    # suite
    @mock.patch('pulp.server.managers.consumer.bind.factory.repo_distributor_manager')
    @mock.patch('pulp.server.managers.consumer.bind.model.Repository.objects')
    def test__add_repo_ids_to_consumer_map(self, *unused_mocks):
        """
        Test the _add_repo_ids_to_consumer_map() function.
        """
        # Set up the consumers
        consumer_ids = ['consumer_1', 'consumer_2', 'consumer_3']
        manager = factory.consumer_manager()
        for consumer_id in consumer_ids:
            manager.register(consumer_id)
        # Create repository bindings. Let's leave consumer_3 unbound.
        bind_manager = BindManager()
        bind_manager.bind('consumer_1', 'repo_1', 'distributor_id', False, {})
        bind_manager.bind('consumer_2', 'repo_1', 'distributor_id', False, {})
        bind_manager.bind('consumer_2', 'repo_2', 'distributor_id', False, {})
        consumer_map = {
            'consumer_1': {'repo_ids': []},
            'consumer_2': {'repo_ids': []},
            'consumer_3': {'repo_ids': []}}

        _add_repo_ids_to_consumer_map(consumer_ids, consumer_map)

        expected_consumer_map = {
            'consumer_1': {'repo_ids': ['repo_1']},
            'consumer_2': {'repo_ids': ['repo_1', 'repo_2']},
            'consumer_3': {'repo_ids': []}}

        # The order of repo_ids is not important, so we'll use the
        # assert_equal_ignoring_list_order, which will compare the lists as sets
        self.assert_equal_ignoring_list_order(consumer_map, expected_consumer_map)


class TestFormatReport(base.PulpServerTests, base.RecursiveUnorderedListComparisonMixin):
    """
    Test the _add_repo_ids_to_consumer_map() function.
    """
    def test__format_report(self):
        """
        Test the _format_report() function.
        """
        applicability_map = {
            frozenset(['consumer_1']): {'type_1': ['unit_1']},
            frozenset(['consumer_1', 'consumer_2']): {'type_2': ['unit_2']}}

        report = _format_report(applicability_map)

        expected_report = [{'consumers': ['consumer_1'],
                            'applicability': {'type_1': ['unit_1']}},
                           {'consumers': ['consumer_1', 'consumer_2'],
                            'applicability': {'type_2': ['unit_2']}}]
        # The order of lists found in the output isn't important, so we can use
        # assert_equal_ignoring_list_order to compare the output and expected output as sets
        self.assert_equal_ignoring_list_order(report, expected_report)

    def test__format_report_removes_empty_consumer_lists(self):
        """
        Test the _format_report() function with applicability data that doesn't apply to
        any consumers.
        """
        applicability_map = {
            frozenset(['consumer_1']): {'type_1': ['unit_1']},
            frozenset(['consumer_1', 'consumer_2']): {'type_2': ['unit_2']},
            frozenset([]): {'type_3': ['unit_3']}}

        report = _format_report(applicability_map)

        expected_report = [{'consumers': ['consumer_1'],
                            'applicability': {'type_1': ['unit_1']}},
                           {'consumers': ['consumer_1', 'consumer_2'],
                            'applicability': {'type_2': ['unit_2']}}]
        # The order of lists found in the output isn't important, so we can use
        # assert_equal_ignoring_list_order to compare the output and expected output as sets
        self.assert_equal_ignoring_list_order(report, expected_report)


class TestGetApplicabilityMap(base.PulpServerTests):
    """
    Test the _get_applicability_map() function.
    """
    def tearDown(self):
        """
        Empty the collections that were written to during this test suite.
        """
        super(TestGetApplicabilityMap, self).tearDown()
        RepoProfileApplicability.get_collection().remove()

    def test__get_applicability_map_content_types_none(self):
        """
        Test the _get_applicability_map() function with content_types set to None.
        """
        applicabilities = [
            {'profile_hash': 'hash_1',
             'profile': 'a_profile',
             'repo_id': 'repo_1',
             'applicability': {'type_1': 'a_1'}},
            {'profile_hash': 'hash_1',
             'profile': 'a_profile',
             'repo_id': 'repo_2',
             'applicability': {'type_1': 'a_2'}},
            {'profile_hash': 'hash_2',
             'profile': 'another_profile',
             'repo_id': 'repo_2',
             'applicability': {'type_2': 'a_3'}},
            {'profile_hash': 'hash_3',
             'profile': 'we leave this off the query',
             'repo_id': 'repo_1',
             'applicability': {'type_1': 'a_4'}}]
        for a in applicabilities:
            RepoProfileApplicability.objects.create(a['profile_hash'], a['repo_id'],
                                                    a['profile'], a['applicability'])

        # Leave hash_3 out of the query, so we can make sure it doesn't get returned
        a_map = _get_applicability_map(['hash_1', 'hash_2'], None)

        expected_a_map = {
            ('hash_1', 'repo_1'): {'applicability': {'type_1': 'a_1'}, 'consumers': []},
            ('hash_1', 'repo_2'): {'applicability': {'type_1': 'a_2'}, 'consumers': []},
            ('hash_2', 'repo_2'): {'applicability': {'type_2': 'a_3'}, 'consumers': []}}
        self.assertEqual(a_map, expected_a_map)

    def test__get_applicability_map_content_types_not_none(self):
        """
        Assert that _get_applicability_map() correctly filters out unwanted types when
        content_types is passed.
        """
        applicabilities = [
            {'profile_hash': 'hash_1',
             'profile': 'a_profile',
             'repo_id': 'repo_1',
             'applicability': {'type_1': 'a_1'}},
            {'profile_hash': 'hash_1',
             'profile': 'a_profile',
             'repo_id': 'repo_2',
             'applicability': {'type_1': 'a_2', 'type_2': 'a_5'}},
            {'profile_hash': 'hash_2',
             'profile': 'another_profile',
             'repo_id': 'repo_2',
             'applicability': {'type_2': 'a_3'}},
            {'profile_hash': 'hash_3',
             'profile': 'we leave this off the query',
             'repo_id': 'repo_1',
             'applicability': {'type_1': 'a_4'}}]
        for a in applicabilities:
            RepoProfileApplicability.objects.create(a['profile_hash'], a['repo_id'],
                                                    a['profile'], a['applicability'])

        # Leave hash_3 out of the query, so we can make sure it doesn't get returned
        a_map = _get_applicability_map(['hash_1', 'hash_2'], ['type_1'])

        expected_a_map = {
            ('hash_1', 'repo_1'): {'applicability': {'type_1': 'a_1'}, 'consumers': []},
            ('hash_1', 'repo_2'): {'applicability': {'type_1': 'a_2'}, 'consumers': []}}
        self.assertEqual(a_map, expected_a_map)


class TestGetConsumerApplicabilityMap(base.PulpServerTests,
                                      base.RecursiveUnorderedListComparisonMixin):
    """
    Test the _get_consumer_applicability_map() function.
    """
    def test__get_consumer_applicability_map(self):
        """
        Test the _get_consumer_applicability_map() function.
        """
        a_map = {
            ('hash_1', 'repo_1'): {'applicability': {'type_1': ['a_1']},
                                   'consumers': ['c_1', 'c_2']},
            ('hash_1', 'repo_2'): {'applicability': {'type_1': ['a_2']},
                                   'consumers': ['c_2', 'c_3']},
            # This is the same set of consumers as the first group. The function should
            # combine these two into the same entry in the output. This one has the same
            # content_type as the first one too, so it should combine the units together.
            ('hash_1', 'repo_3'): {'applicability': {'type_1': ['a_3']},
                                   'consumers': ['c_1', 'c_2']},
            # Another one with the same consumers, but this one's applicability is for
            # a different content type, which will still combine them together, but as
            # separate types in the same applicability entry
            ('hash_1', 'repo_4'): {'applicability': {'type_2': ['a_4']},
                                   'consumers': ['c_1', 'c_2']}}

        c_a_map = _get_consumer_applicability_map(a_map)

        expected_c_a_map = {
            frozenset(['c_1', 'c_2']): {'type_1': ['a_1', 'a_3'], 'type_2': ['a_4']},
            frozenset(['c_2', 'c_3']): {'type_1': ['a_2']}}
        self.assert_equal_ignoring_list_order(c_a_map, expected_c_a_map)
