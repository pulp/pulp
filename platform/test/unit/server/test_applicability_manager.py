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
from pulp.server.db.model.consumer import Consumer, RepoProfileApplicability, UnitProfile
from pulp.server.db.model.criteria import Criteria
from pulp.server.managers import factory as factory
from pulp.server.managers.consumer.applicability import (MultipleObjectsReturned,
                                                         DoesNotExist)
import base
import mock_plugins

# -- test cases ---------------------------------------------------------------

class ApplicabilityManagerTests(base.PulpServerTests):

    CONSUMER_IDS = ['test-1', 'test-2']
    FILTER = {'id':{'$in':CONSUMER_IDS}}
    SORT = [{'id':1}]
    CONSUMER_CRITERIA = Criteria(filters=FILTER, sort=SORT)
    REPO_CRITERIA = None
    PROFILE = [{'name':'zsh', 'version':'1.0'}, {'name':'ksh', 'version':'1.0'}]

    def setUp(self):
        base.PulpServerTests.setUp(self)
        Consumer.get_collection().remove()
        UnitProfile.get_collection().remove()
        plugins._create_manager()
        mock_plugins.install()
        profiler, cfg = plugins.get_profiler_by_type('rpm')
        profiler.find_applicable_units = \
            Mock(side_effect=lambda i,r,t,u,c,x:
                 [ApplicabilityReport('mysummary', 'mydetails')])

    def tearDown(self):
        base.PulpServerTests.tearDown(self)
        Consumer.get_collection().remove()
        UnitProfile.get_collection().remove()
        mock_plugins.reset()

    def populate(self):
        manager = factory.consumer_manager()
        for id in self.CONSUMER_IDS:
            manager.register(id)
        manager = factory.consumer_profile_manager()
        for id in self.CONSUMER_IDS:
            manager.create(id, 'rpm', self.PROFILE)

    def test_profiler_no_exception(self):
        # Setup
        self.populate()
        profiler, cfg = plugins.get_profiler_by_type('rpm')
        profiler.find_applicable_units = Mock(side_effect=KeyError)
        # Test
        user_specified_unit_criteria = {'rpm': {"filters": {"name": {"$in":['zsh','ksh']}}},
                                        'mock-type': {"filters": {"name": {"$in":['abc','def']}}}
                                        }
        unit_criteria = {}
        for type_id, criteria in user_specified_unit_criteria.items():
            unit_criteria[type_id] = Criteria.from_client_input(criteria)
        manager = factory.consumer_applicability_manager()
        result = manager.find_applicable_units(self.CONSUMER_CRITERIA, self.REPO_CRITERIA, unit_criteria)
        self.assertTrue(result == {})

    def test_no_exception_for_profiler_notfound(self):
        # Setup
        self.populate()
        # Test
        user_specified_unit_criteria = {'rpm': {"filters": {"name": {"$in":['zsh']}}},
                         'xxx': {"filters": {"name": {"$in":['abc']}}}
                        }
        unit_criteria = {}
        for type_id, criteria in user_specified_unit_criteria.items():
            unit_criteria[type_id] = Criteria.from_client_input(criteria)
        manager = factory.consumer_applicability_manager()
        result = manager.find_applicable_units(self.CONSUMER_CRITERIA, self.REPO_CRITERIA, unit_criteria)
        self.assertTrue(result == {})


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