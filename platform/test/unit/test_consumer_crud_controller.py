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

import mock

import base
import dummy_plugins

from pulp.plugins import loader as plugin_loader
from pulp.server.db.connection import PulpCollection
from pulp.server.db.model import criteria
from pulp.server.db.model.consumer import Consumer
from pulp.server.managers import factory as manager_factory

class ConsumerControllersTests(base.PulpWebserviceTests):

    def setUp(self):
        super(ConsumerControllersTests, self).setUp()
        self.consumer_manager = manager_factory.consumer_manager()
        Consumer.get_collection().remove(safe=True)

    def clean(self):
        super(ConsumerControllersTests, self).clean()
        Consumer.get_collection().remove(safe=True)


class ConsumerAdvancedSearchTests(ConsumerControllersTests):
    @mock.patch('pulp.server.webservices.controllers.base.JSONController.params')
    @mock.patch.object(PulpCollection, 'query')
    def test_basic_search(self, mock_query, mock_params):
        mock_params.return_value = {
            'criteria' : {}
        }
        ret = self.post('/v2/consumers/search/')
        self.assertEqual(ret[0], 200)
        self.assertEqual(mock_query.call_count, 1)
        query_arg = mock_query.call_args[0][0]
        self.assertTrue(isinstance(query_arg, criteria.Criteria))
        # once to get the criteria, once to check for 'bindings'
        self.assertEqual(mock_params.call_count, 2)

    @mock.patch('pulp.server.webservices.controllers.base.JSONController.params')
    @mock.patch.object(PulpCollection, 'query')
    @mock.patch('pulp.server.webservices.controllers.consumers.process_consumers')
    def test_post_calls_process(self, mock_process, mock_query, mock_params):
        """
        Make sure the search calls process_consumers
        """
        mock_params.return_value = {'criteria' : {}}
        status, body = self.post('/v2/consumers/search/')
        self.assertEqual(status, 200)
        self.assertEqual(mock_process.call_count, 1)
        # make sure the 'bindings' argument was False
        self.assertFalse(mock_process.call_args[0][1])

    @mock.patch('pulp.server.webservices.controllers.base.JSONController.params')
    @mock.patch.object(PulpCollection, 'query')
    @mock.patch('pulp.server.webservices.controllers.consumers.process_consumers')
    def test_get_calls_process(self, mock_process, mock_query, mock_params):
        """
        Make sure the search calls process_consumers
        """
        mock_params.return_value = {}
        status, body = self.get('/v2/consumers/search/')
        self.assertEqual(status, 200)
        self.assertEqual(mock_process.call_count, 1)
        # make sure the 'bindings' argument was False
        self.assertFalse(mock_process.call_args[0][1])

    @mock.patch('pulp.server.webservices.controllers.base.JSONController.params')
    @mock.patch.object(PulpCollection, 'query')
    @mock.patch('pulp.server.webservices.controllers.consumers.process_consumers')
    def test_post_with_bindings(self, mock_process, mock_query, mock_params):
        """
        Make sure the search calls process_consumers
        """
        mock_params.return_value = {'criteria' : {}, 'bindings' : True}
        status, body = self.post('/v2/consumers/search/')
        self.assertEqual(status, 200)
        self.assertEqual(mock_process.call_count, 1)
        self.assertTrue(mock_process.call_args[0][1])

    @mock.patch('pulp.server.webservices.controllers.base.JSONController.params')
    @mock.patch.object(PulpCollection, 'query')
    @mock.patch('pulp.server.webservices.controllers.consumers.process_consumers')
    def test_get_with_bindings(self, mock_process, mock_query, mock_params):
        """
        Make sure the search calls process_consumers
        """
        mock_params.return_value = {'bindings' : True}
        status, body = self.get('/v2/consumers/search/')
        self.assertEqual(status, 200)
        self.assertEqual(mock_process.call_count, 1)
        self.assertTrue(mock_process.call_args[0][1])

class ConsumerCollectionTests(ConsumerControllersTests):

    def test_get(self):
        """
        Tests retrieving a list of consumers.
        """

        # Setup
        self.consumer_manager.register('consumer1')
        self.consumer_manager.register('consumer2')

        # Test
        status, body = self.get('/v2/consumers/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(2, len(body))
        self.assertTrue(body[0]['id'].startswith('consumer'))
        self.assertFalse('bindings' in body[0])
        self.assertTrue('_href' in body[0])

    @mock.patch('pulp.server.webservices.controllers.base.JSONController.params')
    @mock.patch.object(PulpCollection, 'query')
    @mock.patch('pulp.server.webservices.controllers.consumers.process_consumers')
    def test_get_with_bindings(self, mock_process, mock_query, mock_params):
        """
        Test that if the 'bindings' parameter is passed in, bindings will be
        requested of the process_consumers function
        """
        mock_params.return_value = {'bindings' : True}
        status, body = self.get('/v2/consumers/')
        self.assertEqual(status, 200)
        self.assertEqual(mock_process.call_count, 1)
        self.assertTrue(mock_process.call_args[0][1])

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
            'id' : 'consumer1',
            'display-name' : 'Consumer 1',
            'description' : 'Test Consumer',
        }

        # Test
        status, body = self.post('/v2/consumers/', params=body)

        # Verify
        self.assertEqual(201, status)

        self.assertEqual(body['id'], 'consumer1')

        consumer = Consumer.get_collection().find_one({'id' : 'consumer1'})
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
        self.consumer_manager.register('existing')

        body = {'id' : 'existing'}

        # Test
        status, body = self.post('/v2/consumers/', params=body)

        # Verify
        self.assertEqual(409, status)


class ConsumerResourceTests(ConsumerControllersTests):

    def test_get(self):
        """
        Tests retrieving a valid consumer.
        """

        # Setup
        self.consumer_manager.register('consumer-1')
        PATH = '/v2/consumers/consumer-1/'

        # Test
        status, body = self.get(PATH)

        # Verify
        self.assertEqual(200, status)
        self.assertEqual('consumer-1', body['id'])
        self.assertTrue('bindings' not in body)
        self.assertTrue('_href' in body)
        self.assertTrue(body['_href'].endswith(PATH))

    @mock.patch('pulp.server.webservices.controllers.base.JSONController.params')
    @mock.patch.object(PulpCollection, 'query')
    @mock.patch('pulp.server.webservices.controllers.consumers.process_consumers')
    def test_get_with_bindings(self, mock_process, mock_query, mock_params):
        """
        Test that if the 'bindings' parameter is passed in, bindings will be
        requested of the process_consumers function
        """
        mock_params.return_value = {'bindings' : True}
        status, body = self.get('/v2/consumers/')
        self.assertEqual(status, 200)
        self.assertEqual(mock_process.call_count, 1)
        self.assertTrue(mock_process.call_args[0][1])

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
        self.consumer_manager.register('doomed')

        # Test
        status, body = self.delete('/v2/consumers/doomed/')

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
        self.consumer_manager.register('turkey', display_name='hungry')
        PATH = '/v2/consumers/turkey/'

        req_body = {'delta' : {'display-name' : 'thanksgiving'}}

        # Test
        status, body = self.put(PATH, params=req_body)

        # Verify
        self.assertEqual(200, status)

        self.assertEqual(body['display_name'], req_body['delta']['display-name'])
        self.assertTrue(body['_href'].endswith(PATH))

        consumer = Consumer.get_collection().find_one({'id' : 'turkey'})
        self.assertEqual(consumer['display_name'], req_body['delta']['display-name'])

    def test_put_invalid_body(self):
        """
        Tests updating a consumer without passing the delta.
        """

        # Setup
        self.consumer_manager.register('pie')

        # Test
        status, body = self.put('/v2/consumers/pie/', params={})

        # Verify
        self.assertEqual(400, status)

    def test_put_missing_consumer(self):
        """
        Tests updating a consumer that doesn't exist.
        """

        # Test
        req_body = {'delta' : {'pie' : 'apple'}}
        status, body = self.put('/v2/consumers/not-there/', params=req_body)

        # Verify
        self.assertEqual(404, status)


class ConsumerPluginsTests(ConsumerControllersTests):

    def setUp(self):
        super(ConsumerPluginsTests, self).setUp()

        plugin_loader._create_loader()
        dummy_plugins.install()

        self.consumer_query_manager = manager_factory.consumer_query_manager()
        self.consumer_bind_manager = manager_factory.consumer_bind_manager()

    def tearDown(self):
        super(ConsumerPluginsTests, self).tearDown()
        dummy_plugins.reset()

