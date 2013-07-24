#!/usr/bin/python
#
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

from mock import Mock

from pulp.plugins.conduits.profiler import ProfilerConduit
from pulp.plugins.loader import api as plugins
from pulp.server.db.model.consumer import Bind, Consumer, RepoProfileApplicability, UnitProfile
from pulp.server.db.model.repository import Repo, RepoDistributor
from pulp.server.db.model.criteria import Criteria
from pulp.server.managers import factory as factory
from pulp.server.managers.consumer.applicability import (MultipleObjectsReturned,
                                                         DoesNotExist)

import base
import mock_plugins

# -- test cases ---------------------------------------------------------------

class ApplicabilityRegenerationManagerTests(base.PulpServerTests):

    CONSUMER_IDS = ['consumer-1', 'consumer-2']
    FILTER = {'id':{'$in':CONSUMER_IDS}}
    SORT = [{'id':1}]
    CONSUMER_CRITERIA = Criteria(filters=FILTER, sort=SORT)
    PROFILE1 = [{'name':'zsh', 'version':'1.0'}, {'name':'ksh', 'version':'1.0'}]
    PROFILE2 = [{'name':'zsh', 'version':'2.0'}, {'name':'ksh', 'version':'2.0'}]
    REPO_IDS = ['repo-1','repo-2']
    REPO_CRITERIA = Criteria(filters={'id':{'$in':REPO_IDS}}, sort=[{'id':1}])
    YUM_DISTRIBUTOR_ID = 'yum_distributor'

    def setUp(self):
        base.PulpServerTests.setUp(self)
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        Consumer.get_collection().remove()
        UnitProfile.get_collection().remove()
        RepoProfileApplicability.get_collection().remove()
        plugins._create_manager()
        mock_plugins.install()

        rpm_pkg_profiler, cfg = plugins.get_profiler_by_type('rpm')
        rpm_pkg_profiler.calculate_applicable_units = \
            Mock(side_effect=lambda t,p,r,c,x:
                 ['rpm-1', 'rpm-2'])
        rpm_errata_profiler, cfg = plugins.get_profiler_by_type('erratum')
        rpm_errata_profiler.calculate_applicable_units = \
            Mock(side_effect=lambda t,p,r,c,x:
                 ['errata-1', 'errata-2'])

    def tearDown(self):
        base.PulpServerTests.tearDown(self)
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        Consumer.get_collection().remove()
        UnitProfile.get_collection().remove()
        RepoProfileApplicability.get_collection().remove()
        mock_plugins.reset()

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
        repo_manager = factory.repo_manager()
        distributor_manager = factory.repo_distributor_manager()
        # Create repos and add distributor
        for repo_id in self.REPO_IDS:
            repo_manager.create_repo(repo_id)
            distributor_manager.add_distributor(
                                                repo_id,
                                                'mock-distributor',
                                                {},
                                                True,
                                                self.YUM_DISTRIBUTOR_ID)

    def populate_bindings(self):
        self.populate_repos()
        bind_manager = factory.consumer_bind_manager()
        # Add bindings for the given repos and consumers
        for consumer_id in self.CONSUMER_IDS:
            for repo_id in self.REPO_IDS:
                bind_manager.bind(consumer_id, repo_id, self.YUM_DISTRIBUTOR_ID, False, {})

    # Applicability regeneration with consumer criteria
 
    def test_regenerate_applicability_for_consumers_with_different_profiles(self):
        # Setup
        self.populate_consumers_different_profiles()
        self.populate_bindings()
        # Test
        manager = factory.applicability_regeneration_manager()
        manager.regenerate_applicability_for_consumers(self.CONSUMER_CRITERIA)
        # Verify
        applicability_list = list(RepoProfileApplicability.get_collection().find())
        self.assertEqual(len(applicability_list), 4)
        expected_applicability = {'rpm': ['rpm-1', 'rpm-2'], 'erratum': ['errata-1', u'errata-2']}
        for applicability in applicability_list:
            self.assertEqual(applicability['applicability'], expected_applicability)
            self.assertTrue(applicability['profile']['profile'] in [self.PROFILE1, self.PROFILE2])

    def test_regenerate_applicability_for_consumers_with_same_profiles(self):
        # Setup
        self.populate_consumers()
        self.populate_bindings()
        # Test
        manager = factory.applicability_regeneration_manager()
        manager.regenerate_applicability_for_consumers(self.CONSUMER_CRITERIA)
        # Verify
        applicability_list = list(RepoProfileApplicability.get_collection().find())
        self.assertEqual(len(applicability_list), 2)
        expected_applicability = {'rpm': ['rpm-1', 'rpm-2'], 'erratum': ['errata-1', u'errata-2']}
        for applicability in applicability_list:
            self.assertEqual(applicability['profile']['profile'], self.PROFILE1)
            self.assertEqual(applicability['applicability'], expected_applicability)

    def test_regenerate_applicability_for_empty_consumer_criteria(self):
        # Setup
        self.populate_consumers()
        self.populate_bindings()
        # Test
        manager = factory.applicability_regeneration_manager()
        manager.regenerate_applicability_for_consumers(Criteria())
        # Verify
        applicability_list = list(RepoProfileApplicability.get_collection().find())
        self.assertEqual(len(applicability_list), 2)
        expected_applicability = {'rpm': ['rpm-1', 'rpm-2'], 'erratum': ['errata-1', u'errata-2']}
        for applicability in applicability_list:
            self.assertEqual(applicability['profile']['profile'], self.PROFILE1)
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

    def test_regenerate_applicability_for_consumers_profiler_notfound(self):
        # Setup
        self.populate_consumers()
        self.populate_bindings()
        profiler, cfg = plugins.get_profiler_by_type('rpm')
        profiler.calculate_applicable_units = Mock(side_effect=NotImplementedError())
        # Test
        manager = factory.applicability_regeneration_manager()
        manager.regenerate_applicability_for_consumers(self.CONSUMER_CRITERIA)
        # Verify
        applicability_list = list(RepoProfileApplicability.get_collection().find())
        self.assertEqual(len(applicability_list), 2)
        expected_applicability = {'erratum': ['errata-1', u'errata-2']}
        for applicability in applicability_list:
            self.assertEqual(applicability['applicability'], expected_applicability)

    # Applicability regeneration with repo criteria

    def test_regenerate_applicability_for_repos_with_different_consumer_profiles(self):
        # Setup
        self.populate_consumers_different_profiles()
        self.populate_bindings()
        # Test
        manager = factory.applicability_regeneration_manager()
        manager.regenerate_applicability_for_repos(self.REPO_CRITERIA)
        # Verify
        applicability_list = list(RepoProfileApplicability.get_collection().find())
        self.assertEqual(len(applicability_list), 4)
        expected_applicability = {'rpm': ['rpm-1', 'rpm-2'], 'erratum': ['errata-1', u'errata-2']}
        for applicability in applicability_list:
            self.assertEqual(applicability['applicability'], expected_applicability)
            self.assertTrue(applicability['profile']['profile'] in [self.PROFILE1, self.PROFILE2])

    def test_regenerate_applicability_for_repos_with_same_consumer_profiles(self):
        # Setup
        self.populate_consumers()
        self.populate_bindings()
        # Test
        manager = factory.applicability_regeneration_manager()
        manager.regenerate_applicability_for_repos(self.REPO_CRITERIA)
        # Verify
        applicability_list = list(RepoProfileApplicability.get_collection().find())
        self.assertEqual(len(applicability_list), 2)
        expected_applicability = {'rpm': ['rpm-1', 'rpm-2'], 'erratum': ['errata-1', u'errata-2']}
        for applicability in applicability_list:
            self.assertEqual(applicability['profile']['profile'], self.PROFILE1)
            self.assertEqual(applicability['applicability'], expected_applicability)

    def test_regenerate_applicability_for_empty_repo_criteria(self):
        # Setup
        self.populate_consumers()
        self.populate_bindings()
        # Test
        manager = factory.applicability_regeneration_manager()
        manager.regenerate_applicability_for_repos(Criteria())
        # Verify
        applicability_list = list(RepoProfileApplicability.get_collection().find())
        self.assertEqual(len(applicability_list), 2)
        expected_applicability = {'rpm': ['rpm-1', 'rpm-2'], 'erratum': ['errata-1', u'errata-2']}
        for applicability in applicability_list:
            self.assertEqual(applicability['profile']['profile'], self.PROFILE1)
            self.assertEqual(applicability['applicability'], expected_applicability)

    def test_regenerate_applicability_for_repo_criteria_no_bindings(self):
        # Setup
        self.populate_repos()
        # Test
        manager = factory.applicability_regeneration_manager()
        manager.regenerate_applicability_for_repos(self.REPO_CRITERIA)
        # Verify
        applicability_list = list(RepoProfileApplicability.get_collection().find())
        self.assertEqual(applicability_list, [])

    def test_regenerate_applicability_for_repos_profiler_notfound(self):
        # Setup
        self.populate_consumers()
        self.populate_bindings()
        profiler, cfg = plugins.get_profiler_by_type('rpm')
        profiler.calculate_applicable_units = Mock(side_effect=NotImplementedError())
        # Test
        manager = factory.applicability_regeneration_manager()
        manager.regenerate_applicability_for_repos(self.REPO_CRITERIA)
        # Verify
        applicability_list = list(RepoProfileApplicability.get_collection().find())
        self.assertEqual(len(applicability_list), 2)
        expected_applicability = {'erratum': ['errata-1', u'errata-2']}
        for applicability in applicability_list:
            self.assertEqual(applicability['applicability'], expected_applicability)


class TestRepoProfileApplicabilityManager(base.PulpServerTests):
    """
    Test the RepoProfileApplicabilityManager.
    """
    def setUp(self):
        """
        Store the collection on self.
        """
        self.collection = RepoProfileApplicability.get_collection()

    def tearDown(self):
        """
        Clean up the collection.
        """
        self.collection.drop()

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
        a_3 = RepoProfileApplicability.objects.create(
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
        a_1 = RepoProfileApplicability.objects.create(
            profile_hash='hash_1', repo_id='repo_1', profile='profile',
            applicability='applicability')
        a_2 = RepoProfileApplicability.objects.create(
            profile_hash='hash_2', repo_id='repo_1', profile='profile',
            applicability='applicability')
        a_3 = RepoProfileApplicability.objects.create(
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
        a_1 = RepoProfileApplicability.objects.create(
            profile_hash='hash_1', repo_id='repo_1', profile='profile',
            applicability='applicability')
        a_2 = RepoProfileApplicability.objects.create(
            profile_hash='hash_2', repo_id='repo_1', profile='profile',
            applicability='applicability')
        a_3 = RepoProfileApplicability.objects.create(
            profile_hash='hash_1', repo_id='repo_2', profile='profile',
            applicability='applicability')

        self.assertRaises(MultipleObjectsReturned, RepoProfileApplicability.objects.get, {})

    def test_get_matches_none(self):
        """
        Test the get() method, when it matches no object.
        """
        self.assertRaises(DoesNotExist, RepoProfileApplicability.objects.get, {})
