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

import mock

from pulp.server.db.model.consumer import (Bind, Consumer, RepoProfileApplicability,
                                           UnitProfile)
from pulp.server.db.model.criteria import Criteria
from pulp.server.managers import factory as factory
from pulp.server.managers.consumer.applicability import (
    _add_consumers_to_applicability_map, _add_profiles_to_consumer_map_and_get_hashes,
    _add_repo_ids_to_consumer_map, _format_report, _get_applicability_map,
    _get_consumer_applicability_map, DoesNotExist, MultipleObjectsReturned,
    retrieve_consumer_applicability)
from pulp.server.managers.consumer.bind import BindManager
from pulp.server.managers.consumer.profile import ProfileManager
import base


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

        self.assertRaises(MultipleObjectsReturned,
                          RepoProfileApplicability.objects.get, {})

    def test_get_matches_none(self):
        """
        Test the get() method, when it matches no object.
        """
        self.assertRaises(DoesNotExist,
                          RepoProfileApplicability.objects.get, {})


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

    # We mock this because we don't care about consumer history in this test suite, and it
    # saves some DB access time and cleanup
    @mock.patch('pulp.server.managers.consumer.bind.factory.consumer_history_manager')
    # By mocking this, we can avoid having to create repos and distributors for this test
    # suite
    @mock.patch('pulp.server.managers.consumer.bind.factory.repo_distributor_manager')
    def test_consumers_with_same_applicability(self, consumer_history_manager,
                                               repo_distributor_manager):
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

    # We mock this because we don't care about consumer history in this test suite, and it
    # saves some DB access time and cleanup
    @mock.patch('pulp.server.managers.consumer.bind.factory.consumer_history_manager')
    # By mocking this, we can avoid having to create repos and distributors for this test
    # suite
    @mock.patch('pulp.server.managers.consumer.bind.factory.repo_distributor_manager')
    def test_disparate_consumers(self, consumer_history_manager,
                                 repo_distributor_manager):
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

    # We mock this because we don't care about consumer history in this test suite, and it
    # saves some DB access time and cleanup
    @mock.patch('pulp.server.managers.consumer.bind.factory.consumer_history_manager')
    # By mocking this, we can avoid having to create repos and distributors for this test
    # suite
    @mock.patch('pulp.server.managers.consumer.bind.factory.repo_distributor_manager')
    def test_empty_type_limiting(self, consumer_history_manager,
                                 repo_distributor_manager):
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

    # We mock this because we don't care about consumer history in this test suite, and it
    # saves some DB access time and cleanup
    @mock.patch('pulp.server.managers.consumer.bind.factory.consumer_history_manager')
    # By mocking this, we can avoid having to create repos and distributors for this test
    # suite
    @mock.patch('pulp.server.managers.consumer.bind.factory.repo_distributor_manager')
    def test_limit_by_type(self, consumer_history_manager, repo_distributor_manager):
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

    # We mock this because we don't care about consumer history in this test suite, and it
    # saves some DB access time and cleanup
    @mock.patch('pulp.server.managers.consumer.bind.factory.consumer_history_manager')
    # By mocking this, we can avoid having to create repos and distributors for this test
    # suite
    @mock.patch('pulp.server.managers.consumer.bind.factory.repo_distributor_manager')
    def test_mixed_case(self, consumer_history_manager, repo_distributor_manager):
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

    # We mock this because we don't care about consumer history in this test suite, and it
    # saves some DB access time and cleanup
    @mock.patch('pulp.server.managers.consumer.bind.factory.consumer_history_manager')
    # By mocking this, we can avoid having to create repos and distributors for this test
    # suite
    @mock.patch('pulp.server.managers.consumer.bind.factory.repo_distributor_manager')
    def test_multiple_applicability_data_matches(self, consumer_history_manager,
                                                 repo_distributor_manager):
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

    # We mock this because we don't care about consumer history in this test suite, and it
    # saves some DB access time and cleanup
    @mock.patch('pulp.server.managers.consumer.bind.factory.consumer_history_manager')
    # By mocking this, we can avoid having to create repos and distributors for this test
    # suite
    @mock.patch('pulp.server.managers.consumer.bind.factory.repo_distributor_manager')
    def test_non_matching_consumer_ids(self, consumer_history_manager,
                                       repo_distributor_manager):
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

    # We mock this because we don't care about consumer history in this test suite, and it
    # saves some DB access time and cleanup
    @mock.patch('pulp.server.managers.consumer.bind.factory.consumer_history_manager')
    # By mocking this, we can avoid having to create repos and distributors for this test
    # suite
    @mock.patch('pulp.server.managers.consumer.bind.factory.repo_distributor_manager')
    def test_single_consumer(self, consumer_history_manager,
                             repo_distributor_manager):
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
        self.assertEqual(set([p['profile_hash'] \
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
    # By mocking this, we can avoid having to create repos and distributors for this test
    # suite
    @mock.patch('pulp.server.managers.consumer.bind.factory.repo_distributor_manager')
    def test__add_repo_ids_to_consumer_map(self, consumer_history_manager,
                                                 repo_distributor_manager):
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
        a_map = _get_applicability_map(['hash_1', 'hash_2'],
                                                            ['type_1'])

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
