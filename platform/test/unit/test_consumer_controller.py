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

import time
import unittest

import mock

import base
import logging
import mock_plugins
import mock_agent
import json
import urllib
from pulp.plugins.loader import api as plugin_api
from pulp.plugins.model import ApplicabilityReport
from pulp.plugins.loader import api as plugin_api
from pulp.server.managers import factory
from pulp.server.db.model.consumer import Consumer, Bind, UnitProfile
from pulp.server.db.model.repository import Repo, RepoDistributor
from pulp.server.webservices.controllers import consumers


class ConsumerTest(base.PulpWebserviceTests):

    CONSUMER_ID = 'test-consumer'
    REPO_ID = 'test-repo'
    DISTRIBUTOR_ID = 'dist-1'
    DISTRIBUTOR_TYPE_ID = 'mock-distributor'

    def setUp(self):
        base.PulpWebserviceTests.setUp(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        plugin_api._create_manager()
        mock_plugins.install()
        mock_agent.install()

    def tearDown(self):
        base.PulpWebserviceTests.tearDown(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        mock_plugins.reset()

    def test_get(self):
        """
        Tests retrieving a valid consumer.
        """
        # Setup
        manager = factory.consumer_manager()
        manager.register(self.CONSUMER_ID)
        path = '/v2/consumers/%s/' % self.CONSUMER_ID
        # Test
        status, body = self.get(path)
        # Verify
        self.assertEqual(200, status)
        self.assertEqual(self.CONSUMER_ID, body['id'])
        self.assertTrue('bindings' not in body)
        self.assertTrue('_href' in body)
        self.assertTrue(body['_href'].endswith(path))

    def test_get_with_bindings(self):
        """
        Test consumer with bindings.
        """
        # Setup
        manager = factory.repo_manager()
        repo = manager.create_repo(self.REPO_ID)
        manager = factory.repo_distributor_manager()
        manager.add_distributor(
            self.REPO_ID,
            self.DISTRIBUTOR_TYPE_ID,
            {},
            True,
            distributor_id=self.DISTRIBUTOR_ID)
        manager = factory.consumer_manager()
        manager.register(self.CONSUMER_ID)
        manager = factory.consumer_bind_manager()
        bind = manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        # Test
        params = {'bindings':True}
        path = '/v2/consumers/%s/' % self.CONSUMER_ID
        status, body = self.get(path, params=params)
        # Verify
        self.assertEqual(200, status)
        self.assertEqual(self.CONSUMER_ID, body['id'])
        self.assertTrue('_href' in body)
        self.assertTrue(body['_href'].endswith(path))
        self.assertTrue('bindings' in body)
        bindings = body['bindings']
        self.assertEquals(len(bindings), 1)
        self.assertEquals(bindings[0], self.REPO_ID)

    def test_get_with_details(self):
        """
        Test consumer with details.
        """
        # Setup
        manager = factory.repo_manager()
        repo = manager.create_repo(self.REPO_ID)
        manager = factory.repo_distributor_manager()
        manager.add_distributor(
            self.REPO_ID,
            self.DISTRIBUTOR_TYPE_ID,
            {},
            True,
            distributor_id=self.DISTRIBUTOR_ID)
        manager = factory.consumer_manager()
        manager.register(self.CONSUMER_ID)
        manager = factory.consumer_bind_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        # Test
        params = {'details':True}
        path = '/v2/consumers/%s/' % self.CONSUMER_ID
        status, body = self.get(path, params=params)
        # Verify
        self.assertEqual(200, status)
        self.assertEqual(self.CONSUMER_ID, body['id'])
        self.assertTrue('_href' in body)
        self.assertTrue(body['_href'].endswith(path))
        self.assertTrue('bindings' in body)
        bindings = body['bindings']
        self.assertEquals(len(bindings), 1)
        self.assertEquals(bindings[0], self.REPO_ID)

    def test_get_missing_consumer(self):
        """
        Tests that a 404 is returned when getting a consumer that doesn't exist.
        """
        # Test
        status, body = self.get('/v2/consumers/foo/')
        # Verify
        self.assertEqual(404, status)

    def test_delete(self):
        """
        Tests unregistering an existing consumer.
        """
        # Setup
        manager = factory.consumer_manager()
        manager.register(self.CONSUMER_ID)
        # Test
        path = '/v2/consumers/%s/' % self.CONSUMER_ID
        status, body = self.delete(path)
        # Verify
        self.assertEqual(200, status)

        consumer = Consumer.get_collection().find_one({'id' : 'doomed'})
        self.assertTrue(consumer is None)

    def test_delete_missing_consumer(self):
        """
        Tests deleting a consumer that isn't there.
        """
        # Test
        status, body = self.delete('/v2/consumers/fake/')
        # Verify
        self.assertEqual(404, status)

    def test_put(self):
        """
        Tests using put to update a consumer.
        """
        # Setup
        manager = factory.consumer_manager()
        manager.register(self.CONSUMER_ID, display_name='hungry')
        path = '/v2/consumers/%s/' % self.CONSUMER_ID
        body = {'delta' : {'display-name' : 'thanksgiving'}}
        # Test
        status, body = self.put(path, params=body)
        # Verify
        self.assertEqual(200, status)
        self.assertEqual(body['display_name'], 'thanksgiving')
        self.assertTrue(body['_href'].endswith(path))
        collection = Consumer.get_collection()
        consumer = collection.find_one({'id':self.CONSUMER_ID})
        self.assertEqual(consumer['display_name'], 'thanksgiving')

    def test_put_invalid_body(self):
        """
        Tests updating a consumer without passing the delta.
        """
        # Setup
        manager = factory.consumer_manager()
        manager.register('pie')
        # Test
        status, body = self.put('/v2/consumers/pie/', params={})
        # Verify
        self.assertEqual(400, status)

    def test_put_missing_consumer(self):
        """
        Tests updating a consumer that doesn't exist.
        """
        # Test
        body = {'delta' : {'pie' : 'apple'}}
        status, body = self.put('/v2/consumers/not-there/', params=body)
        # Verify
        self.assertEqual(404, status)


class ConsumersTest(base.PulpWebserviceTests):

    CONSUMER_IDS = ('test-consumer_1', 'test-consumer_2')
    REPO_ID = 'test-repo'
    DISTRIBUTOR_ID = 'dist-1'
    DISTRIBUTOR_TYPE_ID = 'mock-distributor'

    def setUp(self):
        base.PulpWebserviceTests.setUp(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        plugin_api._create_manager()
        mock_plugins.install()
        mock_agent.install()

    def tearDown(self):
        base.PulpWebserviceTests.tearDown(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        mock_plugins.reset()

    def populate(self, bindings=False):
        if bindings:
            manager = factory.repo_manager()
            repo = manager.create_repo(self.REPO_ID)
            manager = factory.repo_distributor_manager()
            manager.add_distributor(
                self.REPO_ID,
                self.DISTRIBUTOR_TYPE_ID,
                {},
                True,
                distributor_id=self.DISTRIBUTOR_ID)
        for id in self.CONSUMER_IDS:
            manager = factory.consumer_manager()
            manager.register(id)
            if bindings:
                manager = factory.consumer_bind_manager()
                manager.bind(id, self.REPO_ID, self.DISTRIBUTOR_ID)

    def validate(self, body, bindings=False):
        if bindings:
            self.assertEqual(len(self.CONSUMER_IDS), len(body))
            fetched = dict([(c['id'],c) for c in body])
            for id in self.CONSUMER_IDS:
                consumer = fetched[id]
                self.assertEquals(consumer['id'], id)
                self.assertTrue('_href' in consumer)
                self.assertTrue('bindings' in consumer)
                bindings = consumer['bindings']
                self.assertEquals(len(bindings), 1)
                self.assertEquals(bindings[0], self.REPO_ID)
        else:
            self.assertEqual(len(self.CONSUMER_IDS), len(body))
            fetched = dict([(c['id'],c) for c in body])
            for id in self.CONSUMER_IDS:
                consumer = fetched[id]
                self.assertEquals(consumer['id'], id)
                self.assertTrue('_href' in consumer)
                self.assertFalse('bindings' in body)

    def test_get(self):
        """
        Tests retrieving a list of consumers.
        """
        # Setup
        self.populate()
        # Test
        status, body = self.get('/v2/consumers/')
        # Verify
        self.assertEqual(200, status)
        self.validate(body)

    def test_get_with_details(self):
        """
        Tests retrieving a list of consumers with details.
        """
        # Setup
        self.populate(True)
        # Test
        status, body = self.get('/v2/consumers/?details=1')
        # Verify
        self.assertEqual(200, status)
        self.validate(body, True)

    def test_get_with_bindings(self):
        """
        Tests retrieving a list of consumers with bindings.
        """
        # Setup
        self.populate(True)
        # Test
        status, body = self.get('/v2/consumers/?bindings=1')
        # Verify
        self.assertEqual(200, status)
        self.validate(body, True)

    def test_get_no_consumers(self):
        """
        Tests that an empty list is returned when no consumers are present.
        """
        # Test
        status, body = self.get('/v2/consumers/')
        # Verify
        self.assertEqual(200, status)
        self.assertEqual(0, len(body))

    def test_post(self):
        """
        Tests using post to register a consumer.
        """
        # Setup
        body = {
            'id' : self.CONSUMER_IDS[0],
            'display-name' : 'Consumer 1',
            'description' : 'Test Consumer',
        }
        # Test
        status, body = self.post('/v2/consumers/', params=body)
        # Verify
        self.assertEqual(201, status)
        self.assertEqual(body['id'], self.CONSUMER_IDS[0])
        collection = Consumer.get_collection()
        consumer = collection.find_one({'id' : self.CONSUMER_IDS[0]})
        self.assertTrue(consumer is not None)

    def test_post_bad_data(self):
        """
        Tests registering a consumer with invalid data.
        """
        # Setup
        body = {'id' : 'HA! This looks so totally invalid'}
        # Test
        status, body = self.post('/v2/consumers/', params=body)
        print body
        # Verify
        self.assertEqual(400, status)

    def test_post_conflict(self):
        """
        Tests creating a consumer with an existing ID.
        """
        # Setup
        manager = factory.consumer_manager()
        manager.register(self.CONSUMER_IDS[0])
        body = {'id' : self.CONSUMER_IDS[0]}
        # Test
        status, body = self.post('/v2/consumers/', params=body)
        # Verify
        self.assertEqual(409, status)


class TestSearch(ConsumersTest):

    FILTER = {'id':{'$in':ConsumersTest.CONSUMER_IDS}}
    SORT = [('id','ascending')]
    CRITERIA = dict(filters=FILTER, sort=SORT)

    def test_get(self):
        # Setup
        self.populate()
        # Test
        status, body = self.get('/v2/consumers/search/')
        # Verify
        self.assertEqual(200, status)
        self.validate(body)

    def test_get_with_details(self):
        # Setup
        self.populate(True)
        # Test
        status, body = self.get('/v2/consumers/search/?details=1')
        # Verify
        self.assertEqual(200, status)
        self.validate(body, True)

    def test_get_with_bindings(self):
        # Setup
        self.populate(True)
        # Test
        status, body = self.get('/v2/consumers/search/?bindings=1')
        # Verify
        self.assertEqual(200, status)
        self.validate(body, True)

    def test_post(self):
        # Setup
        self.populate()
        # Test
        body = {'criteria':self.CRITERIA}
        status, body = self.post('/v2/consumers/search/', body)
        # Verify
        self.validate(body)

    def test_post_with_details(self):
        # Setup
        self.populate(True)
        # Test
        body = {'criteria':self.CRITERIA, 'details':True}
        status, body = self.post('/v2/consumers/search/', body)
        # Verify
        self.assertEqual(200, status)
        self.validate(body, True)

    def test_post_with_bindings(self):
        # Setup
        self.populate(True)
        # Test
        body = {'criteria':self.CRITERIA, 'bindings':True}
        status, body = self.post('/v2/consumers/search/', body)
        # Verify
        self.assertEqual(200, status)
        self.validate(body, True)


class BindTest(base.PulpWebserviceTests):

    CONSUMER_ID = 'test-consumer'
    REPO_ID = 'test-repo'
    DISTRIBUTOR_ID = 'dist-1'
    DISTRIBUTOR_TYPE_ID = 'mock-distributor'
    QUERY = dict(
        consumer_id=CONSUMER_ID,
        repo_id=REPO_ID,
        distributor_id=DISTRIBUTOR_ID,
    )
    PAYLOAD = dict(
        server_name='pulp.redhat.com',
        relative_path='/repos/content/repoA',
        protocols=['https',],
        gpg_keys=['key1',],
        ca_cert='MY-CA',
        client_cert='MY-CLIENT-CERT')

    def setUp(self):
        base.PulpWebserviceTests.setUp(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        plugin_api._create_manager()
        mock_plugins.install()
        mock_agent.install()

    def tearDown(self):
        base.PulpWebserviceTests.tearDown(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        mock_plugins.reset()

    def populate(self):
        manager = factory.repo_manager()
        repo = manager.create_repo(self.REPO_ID)
        manager = factory.repo_distributor_manager()
        manager.add_distributor(
            self.REPO_ID,
            self.DISTRIBUTOR_TYPE_ID,
            {},
            True,
            distributor_id=self.DISTRIBUTOR_ID)
        mock_plugins.MOCK_DISTRIBUTOR.create_consumer_payload.return_value=self.PAYLOAD
        manager = factory.consumer_manager()
        manager.register(self.CONSUMER_ID)

    def test_get_bind(self):
        # Setup
        self.populate()
        # Test
        manager = factory.consumer_bind_manager()
        bind = manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        # Test
        path = '/v2/consumers/%s/bindings/%s/%s/' % \
            (self.CONSUMER_ID,
             self.REPO_ID,
             self.DISTRIBUTOR_ID)
        status, body = self.get(path)
        self.assertEquals(status, 200)
        self.assertTrue(body is not None)
        self.assertEquals(body['consumer_id'], self.CONSUMER_ID)
        self.assertEquals(body['repo_id'], self.REPO_ID)
        self.assertEquals(body['distributor_id'], self.DISTRIBUTOR_ID)
        self.assertTrue('_href' in body)

    def test_get_bind_by_consumer(self):
        # Setup
        self.populate()
        # Test
        manager = factory.consumer_bind_manager()
        bind = manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        # Test
        path = '/v2/consumers/%s/bindings/' % self.CONSUMER_ID
        status, body = self.get(path)
        self.assertEquals(status, 200)
        self.assertEquals(len(body), 1)
        bind = body[0]
        self.assertEquals(bind['consumer_id'], self.CONSUMER_ID)
        self.assertEquals(bind['repo_id'], self.REPO_ID)
        self.assertEquals(bind['distributor_id'], self.DISTRIBUTOR_ID)
        self.assertTrue('_href' in bind)
        self.assertEquals(bind['details'], self.PAYLOAD)
        self.assertEquals(bind['type_id'], self.DISTRIBUTOR_TYPE_ID)

    def test_get_bind_by_consumer_and_repo(self):
        # Setup
        self.populate()
        # Test
        manager = factory.consumer_bind_manager()
        bind = manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        # Test
        path = '/v2/consumers/%s/bindings/%s/' % (self.CONSUMER_ID, self.REPO_ID)
        status, body = self.get(path)
        self.assertEquals(status, 200)
        self.assertEquals(len(body), 1)
        bind = body[0]
        self.assertEquals(bind['consumer_id'], self.CONSUMER_ID)
        self.assertEquals(bind['repo_id'], self.REPO_ID)
        self.assertEquals(bind['distributor_id'], self.DISTRIBUTOR_ID)
        self.assertTrue('_href' in bind)
        self.assertEquals(bind['details'], self.PAYLOAD)
        self.assertEquals(bind['type_id'], self.DISTRIBUTOR_TYPE_ID)

    def test_bind(self):
        # Setup
        self.populate()
        # Test
        path = '/v2/consumers/%s/bindings/' % self.CONSUMER_ID
        body = dict(
            repo_id=self.REPO_ID,
            distributor_id=self.DISTRIBUTOR_ID,)
        status, body = self.post(path, body)
        # Verify
        manager = factory.consumer_bind_manager()
        self.assertEquals(status, 201)
        binds = manager.find_by_consumer(self.CONSUMER_ID)
        self.assertEquals(len(binds), 1)
        bind = binds[0]
        for k in ('consumer_id', 'repo_id', 'distributor_id'):
            self.assertEquals(bind[k], body[k])

    def test_unbind(self):
        # Setup
        self.populate()
        manager = factory.consumer_bind_manager()
        bind = manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        # Test
        path = '/v2/consumers/%s/bindings/%s/%s/' % \
            (self.CONSUMER_ID,
             self.REPO_ID,
             self.DISTRIBUTOR_ID)
        status, body = self.delete(path)
        # Verify
        self.assertEquals(status, 200)
        binds = manager.find_by_consumer(self.CONSUMER_ID)
        self.assertEquals(len(binds), 0)

    #
    # Failure Cases
    #

    def test_bind_missing_consumer(self):
        # Setup
        self.populate()
        collection = Consumer.get_collection()
        collection.remove({})
        # Test
        path = '/v2/consumers/%s/bindings/' % self.CONSUMER_ID
        body = dict(
            repo_id=self.REPO_ID,
            distributor_id=self.DISTRIBUTOR_ID,)
        status, body = self.post(path, body)
        # Verify
        manager = factory.consumer_bind_manager()
        self.assertEquals(status, 404)
        binds = manager.find_by_consumer(self.CONSUMER_ID)
        self.assertEquals(len(binds), 0)

    def test_bind_missing_distributor(self):
        # Setup
        self.populate()
        collection = RepoDistributor.get_collection()
        collection.remove({})
        # Test
        path = '/v2/consumers/%s/bindings/' % self.CONSUMER_ID
        body = dict(
            repo_id=self.REPO_ID,
            distributor_id=self.DISTRIBUTOR_ID,)
        status, body = self.post(path, body)
        # Verify
        manager = factory.consumer_bind_manager()
        self.assertEquals(status, 404)
        binds = manager.find_by_consumer(self.CONSUMER_ID)
        self.assertEquals(len(binds), 0)


class ContentTest(base.PulpWebserviceTests):

    CONSUMER_ID = 'test-consumer'
    REPO_ID = 'test-repo'
    DISTRIBUTOR_ID = 'test-distributor'

    def setUp(self):
        base.PulpWebserviceTests.setUp(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        plugin_api._create_manager()
        mock_plugins.install()
        mock_agent.install()

    def tearDown(self):
        base.PulpWebserviceTests.tearDown(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        mock_plugins.reset()

    def populate(self):
        config = {'key1' : 'value1', 'key2' : None}
        manager = factory.repo_manager()
        repo = manager.create_repo(self.REPO_ID)
        manager = factory.repo_distributor_manager()
        manager.add_distributor(
            self.REPO_ID,
            'mock-distributor',
            config,
            True,
            distributor_id=self.DISTRIBUTOR_ID)
        manager = factory.consumer_manager()
        manager.register(self.CONSUMER_ID)

    def test_install(self):
        # Setup
        self.populate()
        # Test
        unit_key = dict(name='zsh')
        unit = dict(type_id='rpm', unit_key=unit_key)
        units = [unit,]
        options = dict(importkeys=True)
        path = '/v2/consumers/%s/actions/content/install/' % self.CONSUMER_ID
        body = dict(
            units=units,
            options=options,)
        self.set_success()
        status, body = self.post(path, body)
        # Verify
        self.assertEquals(status, 200)

    def test_update(self):
        # Setup
        self.populate()
        # Test
        unit_key = dict(name='gofer', version='0.66')
        unit = dict(type_id='rpm', unit_key=unit_key)
        units = [unit,]
        options = dict(importkeys=True)
        path = '/v2/consumers/%s/actions/content/update/' % self.CONSUMER_ID
        body = dict(
            units=units,
            options=options,)
        self.set_success()
        status, body = self.post(path, body)
        # Verify
        self.assertEquals(status, 200)

    def test_uninstall(self):
        # Setup
        self.populate()
        # Test
        unit_key = dict(name='zsh')
        unit = dict(type_id='rpm', unit_key=unit_key)
        units = [unit,]
        options = dict(importkeys=True)
        path = '/v2/consumers/%s/actions/content/uninstall/' % self.CONSUMER_ID
        body = dict(
            units=units,
            options=options,)
        self.set_success()
        status, body = self.post(path, body)
        # Verify
        self.assertEquals(status, 200)


class TestProfiles(base.PulpWebserviceTests):

    CONSUMER_ID = 'test-consumer'
    TYPE_1 = 'type-1'
    TYPE_2 = 'type-2'
    PROFILE_1 = {'name':'zsh', 'version':'1.0'}
    PROFILE_2 = {'name':'ksh', 'version':'2.0', 'arch':'x86_64'}

    def setUp(self):
        self.logger = logging.getLogger('pulp')
        base.PulpWebserviceTests.setUp(self)
        Consumer.get_collection().remove()
        UnitProfile.get_collection().remove()

    def tearDown(self):
        base.PulpWebserviceTests.tearDown(self)
        Consumer.get_collection().remove()
        UnitProfile.get_collection().remove()

    def populate(self):
        manager = factory.consumer_manager()
        manager.register(self.CONSUMER_ID)

    def sort(self, profiles):
        _sorted = []
        d = dict([(p['content_type'],p) for p in profiles])
        for k in sorted(d.keys()):
            _sorted.append(d[k])
        return _sorted

    def test_post(self):
        # Setup
        self.populate()
        # Test
        path = '/v2/consumers/%s/profiles/' % self.CONSUMER_ID
        body = dict(content_type=self.TYPE_1, profile=self.PROFILE_1)
        status, body = self.post(path, body)
        # Verify
        self.assertEqual(status, 201)
        self.assertEqual(body['consumer_id'], self.CONSUMER_ID)
        self.assertEqual(body['content_type'], self.TYPE_1)
        self.assertEqual(body['profile'], self.PROFILE_1)
        manager = factory.consumer_profile_manager()
        profile = manager.get_profile(self.CONSUMER_ID, self.TYPE_1)
        for key in ('consumer_id', 'content_type', 'profile'):
            self.assertEqual(body[key], profile[key])

    def test_put(self):
        # Setup
        self.populate()
        path = '/v2/consumers/%s/profiles/' % self.CONSUMER_ID
        body = dict(content_type=self.TYPE_1, profile=self.PROFILE_1)
        status, body = self.post(path, body)
        self.assertEqual(status, 201)
        self.assertEqual(body['consumer_id'], self.CONSUMER_ID)
        self.assertEqual(body['content_type'], self.TYPE_1)
        self.assertEqual(body['profile'], self.PROFILE_1)
        # Test
        path = '/v2/consumers/%s/profiles/%s/' % (self.CONSUMER_ID, self.TYPE_1)
        body = dict(profile=self.PROFILE_2)
        status, body = self.put(path, body)
        self.assertEqual(body['consumer_id'], self.CONSUMER_ID)
        self.assertEqual(body['content_type'], self.TYPE_1)
        self.assertEqual(body['profile'], self.PROFILE_2)
        manager = factory.consumer_profile_manager()
        profile = manager.get_profile(self.CONSUMER_ID, self.TYPE_1)
        for key in ('consumer_id', 'content_type', 'profile'):
            self.assertEqual(body[key], profile[key])
        self.assertEquals(profile['profile'], self.PROFILE_2)

    def test_delete(self):
        # Setup
        self.populate()
        manager = factory.consumer_profile_manager()
        manager.create(self.CONSUMER_ID, self.TYPE_1, self.PROFILE_1)
        manager.create(self.CONSUMER_ID, self.TYPE_2, self.PROFILE_2)
        profiles = manager.get_profiles(self.CONSUMER_ID)
        self.assertEquals(len(profiles), 2)
        # Test
        path = '/v2/consumers/%s/profiles/%s/' % (self.CONSUMER_ID, self.TYPE_1)
        status, body = self.delete(path)
        profiles = manager.get_profiles(self.CONSUMER_ID)
        self.assertEquals(len(profiles), 1)
        profile = manager.get_profile(self.CONSUMER_ID, self.TYPE_2)
        self.assertTrue(profile is not None)

    def test_get_all(self):
        # Setup
        self.populate()
        manager = factory.consumer_profile_manager()
        manager.create(self.CONSUMER_ID, self.TYPE_1, self.PROFILE_1)
        manager.create(self.CONSUMER_ID, self.TYPE_2, self.PROFILE_2)
        # Test
        path = '/v2/consumers/%s/profiles/' % self.CONSUMER_ID
        status, body = self.get(path)
        # Verify
        self.assertEqual(status, 200)
        self.assertEqual(len(body), 2)
        body = self.sort(body)
        self.assertEqual(body[0]['consumer_id'], self.CONSUMER_ID)
        self.assertEqual(body[0]['content_type'], self.TYPE_1)
        self.assertEqual(body[0]['profile'], self.PROFILE_1)
        self.assertEqual(body[1]['consumer_id'], self.CONSUMER_ID)
        self.assertEqual(body[1]['content_type'], self.TYPE_2)
        self.assertEqual(body[1]['profile'], self.PROFILE_2)

    def test_get_by_type(self):
        # Setup
        self.populate()
        manager = factory.consumer_profile_manager()
        manager.create(self.CONSUMER_ID, self.TYPE_1, self.PROFILE_1)
        manager.create(self.CONSUMER_ID, self.TYPE_2, self.PROFILE_2)
        # Test
        path = '/v2/consumers/%s/profiles/%s/' % (self.CONSUMER_ID, self.TYPE_1)
        status, body = self.get(path)
        self.assertEqual(status, 200)
        self.assertEqual(body['consumer_id'], self.CONSUMER_ID)
        self.assertEqual(body['content_type'], self.TYPE_1)
        self.assertEqual(body['profile'], self.PROFILE_1)


class TestApplicability(base.PulpWebserviceTests):

    CONSUMER_IDS = ['test-1', 'test-2']
    FILTER = {'id':{'$in':CONSUMER_IDS}}
    SORT = [('id','ascending')]
    CRITERIA = dict(filters=FILTER, sort=SORT)
    UNIT = {'type_id':'errata', 'unit_key':{'name':'security-patch_123'}}
    PROFILE = [1,2,3]
    SUMMARY = 'mysummary'
    DETAILS = 'mydetails'

    PATH = '/v2/consumers/actions/content/applicability/'

    def setUp(self):
        base.PulpWebserviceTests.setUp(self)
        Consumer.get_collection().remove()
        UnitProfile.get_collection().remove()
        plugin_api._create_manager()
        mock_plugins.install()
        profiler = plugin_api.get_profiler_by_type('errata')[0]
        profiler.unit_applicable = \
            mock.Mock(side_effect=lambda i,u,c,x:
                ApplicabilityReport(u, True, self.SUMMARY, self.DETAILS))

    def tearDown(self):
        base.PulpWebserviceTests.tearDown(self)
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

    def test_applicability(self):
        # Setup
        self.populate()
        # Test
        body = dict(criteria=self.CRITERIA, units=[self.UNIT])
        status, body = self.post(self.PATH, body)
        self.assertEquals(status, 200)
        self.assertEquals(len(body), 2)
        for id in self.CONSUMER_IDS:
            report = body[id]
            self.assertEquals(report[0]['unit'], self.UNIT)
            self.assertTrue(report[0]['applicable'])
            self.assertEquals(report[0]['summary'], self.SUMMARY)
            self.assertEquals(report[0]['details'], self.DETAILS)

    def test_missing_values(self):
        # Setup
        self.populate()
        # Test
        body = dict(criteria=self.CRITERIA)
        status, body = self.post(self.PATH, body)
        self.assertEquals(status, 400)
        body = dict(units=[self.UNIT])
        status, body = self.post(self.PATH, body)
        self.assertEquals(status, 400)

    def test_no_consumers(self):
        # Test
        body = dict(criteria=self.CRITERIA, units=[self.UNIT])
        status, body = self.post(self.PATH, body)
        self.assertEquals(status, 200)
        self.assertEquals(len(body), 0)
