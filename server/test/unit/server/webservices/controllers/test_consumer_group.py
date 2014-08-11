#!/usr/bin/python
#
# Copyright (c) 2013 Red Hat, Inc.
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

from .... import base
from pulp.devel import mock_plugins
from pulp.devel.unit.server.base import PulpWebservicesTests
from pulp.plugins.loader import api as plugin_api
from pulp.server.auth import authorization
from pulp.server.db.model.criteria import Criteria
from pulp.server.db.model.consumer import Consumer, ConsumerGroup, Bind
from pulp.server.db.model.repository import Repo, RepoDistributor
from pulp.server.exceptions import OperationPostponed
from pulp.server.managers import factory as managers
from pulp.server.webservices.controllers import consumer_groups

GROUP_ID = 'group_1'
CONSUMER_IDS = ('test_1', 'test_2', 'test_3')
REPO_ID = 'test-repo'
DISTRIBUTOR_ID = 'dist-1'
NOTIFY_AGENT = True
BINDING_CONFIG = {'b': 'b'}
DISTRIBUTOR_TYPE_ID = 'mock-distributor'


class ConsumerGroupAssociationTests(base.PulpWebserviceTests):
    def setUp(self):
        super(ConsumerGroupAssociationTests, self).setUp()
        self.manager = managers.consumer_group_manager()

    def clean(self):
        super(ConsumerGroupAssociationTests, self).clean()
        ConsumerGroup.get_collection().remove()

    @mock.patch.object(Criteria, 'from_client_input', return_value=Criteria())
    @mock.patch('pulp.server.managers.consumer.group.cud.ConsumerGroupManager.associate')
    def test_associate(self, mock_associate, mock_from_client):
        self.manager.create_consumer_group('cg1')

        post_data = {'criteria': {'filters': {'id': {'$in': ['consumer1']}}}}
        status, body = self.post('/v2/consumer_groups/cg1/actions/associate/', post_data)
        self.assertEqual(status, 200)

        self.assertEqual(mock_associate.call_count, 1)
        call_args = mock_associate.call_args[0]
        self.assertEqual(call_args[0], 'cg1')
        # verify that it created and used a Criteria instance
        self.assertEqual(call_args[1], mock_from_client.return_value)
        self.assertEqual(mock_from_client.call_args[0][0],
                         {'filters': {'id': {'$in': ['consumer1']}}})

    @mock.patch.object(Criteria, 'from_client_input', return_value=Criteria())
    @mock.patch('pulp.server.managers.consumer.group.cud.ConsumerGroupManager.unassociate')
    def test_unassociate(self, mock_unassociate, mock_from_client):
        self.manager.create_consumer_group('cg1')

        post_data = {'criteria': {'filters': {'id': {'$in': ['consumer1']}}}}
        status, body = self.post('/v2/consumer_groups/cg1/actions/unassociate/', post_data)
        self.assertEqual(status, 200)

        self.assertEqual(mock_unassociate.call_count, 1)
        call_args = mock_unassociate.call_args[0]
        self.assertEqual(call_args[0], 'cg1')
        # verify that it created and used a Criteria instance
        self.assertEqual(call_args[1], mock_from_client.return_value)
        self.assertEqual(mock_from_client.call_args[0][0],
                         {'filters': {'id': {'$in': ['consumer1']}}})
        

class ContentTest(PulpWebservicesTests):

    @mock.patch('pulp.server.managers.consumer.group.cud.ConsumerGroupManager.install_content')
    def test_install(self, mock_task):
        # Setup
        webservice = consumer_groups.ConsumerGroupContentAction()
        webservice.params = mock.Mock(return_value={'units': 'foo-unit',
                                                    'options': 'bar'})
        mock_task.return_value = 'baz'

        # Test
        self.assertRaises(OperationPostponed, webservice.install, 'consumer-foo')
        mock_task.assert_called_once_with('consumer-foo', 'foo-unit', 'bar')

    @mock.patch('pulp.server.managers.consumer.group.cud.ConsumerGroupManager.update_content')
    def test_update(self, mock_task):
        # Setup
        webservice = consumer_groups.ConsumerGroupContentAction()
        webservice.params = mock.Mock(return_value={'units': 'foo-unit',
                                                    'options': 'bar'})
        mock_task.return_value = 'baz'

        # Test
        self.assertRaises(OperationPostponed, webservice.update, 'consumer-foo')
        mock_task.assert_called_once_with('consumer-foo', 'foo-unit', 'bar')

    @mock.patch('pulp.server.managers.consumer.group.cud.ConsumerGroupManager.uninstall_content')
    def test_uninstall(self, mock_task):
        # Setup
        webservice = consumer_groups.ConsumerGroupContentAction()
        webservice.params = mock.Mock(return_value={'units': 'foo-unit',
                                                    'options': 'bar'})
        mock_task.return_value = 'baz'

        # Test
        self.assertRaises(OperationPostponed, webservice.uninstall, 'consumer-foo')
        mock_task.assert_called_once_with('consumer-foo', 'foo-unit', 'bar')


class BindTestNoWSGI(PulpWebservicesTests):
    """
    Tests that have been converted to no longer require the full web.py stack
    """
    @mock.patch('pulp.server.managers.factory.repo_distributor_manager')
    @mock.patch('pulp.server.managers.factory.repo_query_manager')
    @mock.patch('pulp.server.managers.factory.consumer_group_query_manager')
    @mock.patch('pulp.server.managers.consumer.group.cud.bind')
    def test_bind(self, mock_bind_task, mock_group_query, mock_repo_query, mock_dist_query):
        bindings = consumer_groups.ConsumerGroupBindings()
        bindings.params = mock.Mock(return_value={'repo_id': 'foo-repo',
                                                  'distributor_id': 'bar-distributor',
                                                  'notify_agent': True})
        mock_bind_task.apply_async.return_value.id = 'foo'

        self.assertRaises(OperationPostponed, bindings.POST, 'consumer-group-id')
        mock_bind_task.apply_async.assert_called_once()

        #validate the permissions
        self.validate_auth(authorization.CREATE)

    @mock.patch('pulp.server.managers.factory.repo_distributor_manager')
    @mock.patch('pulp.server.managers.factory.repo_query_manager')
    @mock.patch('pulp.server.managers.factory.consumer_group_query_manager')
    @mock.patch('pulp.server.managers.consumer.group.cud.unbind')
    def test_unbind(self, mock_unbind_task, mock_group_query, mock_repo_query, mock_dist_query):
        binding = consumer_groups.ConsumerGroupBinding()
        mock_unbind_task.apply_async.return_value.id = 'foo'

        self.assertRaises(OperationPostponed, binding.DELETE, 'consumer-group-id', 'repo-id',
                          'dist-id')
        mock_unbind_task.apply_async.assert_called_once()

        #validate the permissions
        self.validate_auth(authorization.DELETE)


class BindTest(base.PulpWebserviceTests):

    def setUp(self):
        super(self.__class__, self).setUp()
        Consumer.get_collection().remove()
        ConsumerGroup.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        plugin_api._create_manager()
        mock_plugins.install()

    def tearDown(self):
        super(self.__class__, self).tearDown()
        Consumer.get_collection().remove()
        ConsumerGroup.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        mock_plugins.reset()

    def populate(self):
        manager = managers.consumer_manager()
        for consumer_id in CONSUMER_IDS:
            manager.register(consumer_id)
        manager = managers.consumer_group_manager()
        manager.create_consumer_group(GROUP_ID)
        for consumer_id in CONSUMER_IDS:
            criteria = Criteria(filters={'id': consumer_id}, fields=['id'])
            manager.associate(GROUP_ID, criteria)
        manager = managers.repo_manager()
        manager.create_repo(REPO_ID)
        manager = managers.repo_distributor_manager()
        manager.add_distributor(
            REPO_ID,
            DISTRIBUTOR_TYPE_ID,
            {},
            True,
            distributor_id=DISTRIBUTOR_ID)

    @mock.patch.object(base.PulpWebserviceTests, 'HEADERS', spec=dict)
    def test_bindings_get_returns_405(self, mock_headers):
        """
        Test that the GET (all or one) calls for consumer group bindings return 405 (Method not
        allowed) as expected since we don't store bindings for a consumer group.
        """
        path = '/v2/consumer_groups/%s/bindings/' % GROUP_ID
        call_status, call_body = self.get(path)
        self.assertEqual(405, call_status)
        path = '/v2/consumer_groups/%s/bindings/%s/%s/' % (GROUP_ID, REPO_ID, DISTRIBUTOR_ID)
        call_status, call_body = self.get(path)
        self.assertEqual(405, call_status)

    def test_bindings_invalid_repo_distributor(self):
        """
        Test pulp.server.webservices.controllers.consumer_groups.ConsumerGroupBindings.POST
        to confirm that when given an invalid distributor id, the binding fails and a 400
        code is returned.
        """
        # Setup
        self.populate()
        path = '/v2/consumer_groups/%s/bindings/' % GROUP_ID
        params = {
            'repo_id': REPO_ID,
            'distributor_id': 'notadistributor'
        }

        # Test
        call_status, call_body = self.post(path, params)
        self.assertEqual(400, call_status)

    def test_bindings_invalid_repo_id(self):
        """
        Test pulp.server.webservices.controllers.consumer_groups.ConsumerGroupBindings.POST
        to confirm that when given an invalid repo id, the binding fails and a 400 code
        is returned.
        """
        # Setup
        self.populate()
        path = '/v2/consumer_groups/%s/bindings/' % GROUP_ID
        params = {
            'repo_id': 'notarepo',
            'distributor_id': DISTRIBUTOR_ID
        }

        # Test
        call_status, call_body = self.post(path, params)
        self.assertEqual(400, call_status)

    def test_bindings_invalid_group_id(self):
        """
        Test pulp.server.webservices.controllers.consumer_groups.ConsumerGroupBindings.POST
        to confirm that when given an invalid group id, the binding fails.
        """
        # Setup
        self.populate()
        path = '/v2/consumer_groups/notagroup/bindings/'
        params = {
            'repo_id': REPO_ID,
            'distributor_id': DISTRIBUTOR_ID
        }

        # Test
        call_status, call_body = self.post(path, params)
        self.assertEqual(404, call_status)

    def test_bindings(self):
        """
        Test pulp.server.webservices.controllers.consumer_groups.ConsumerGroupBindings.POST
        to confirm that when given valid arguments, the binding succeeds.
        """
        # Setup
        self.populate()
        path = '/v2/consumer_groups/%s/bindings/' % GROUP_ID
        params = {
            'repo_id': REPO_ID,
            'distributor_id': DISTRIBUTOR_ID
        }

        # Test
        call_status, call_body = self.post(path, params)
        self.assertEqual(202, call_status)

    def test_unbinding_invalid_repo_distributor(self):
        """
        Test pulp.server.webservices.controllers.consumer_groups.ConsumerGroupBinding.DELETE
        to confirm that when given an invalid distributor id, the binding fails.
        """
        # Setup
        self.populate()
        path = '/v2/consumer_groups/%s/bindings/%s/%s/' % (GROUP_ID, REPO_ID, 'notadistributor')

        # Test
        call_status, call_body = self.delete(path)
        self.assertEqual(404, call_status)

    def test_unbinding_invalid_repo_id(self):
        """
        Test pulp.server.webservices.controllers.consumer_groups.ConsumerGroupBinding.DELETE
        to confirm that when given an invalid repo id, the binding fails.
        """
        # Setup
        self.populate()
        path = '/v2/consumer_groups/%s/bindings/%s/%s/' % (GROUP_ID, 'notarepo', DISTRIBUTOR_ID)

        # Test
        call_status, call_body = self.delete(path)
        self.assertEqual(404, call_status)

    def test_unbinding_invalid_group_id(self):
        """
        Test pulp.server.webservices.controllers.consumer_groups.ConsumerGroupBindings.DELETE
        to confirm that when given an invalid group id, the binding fails.
        """
        # Setup
        self.populate()
        path = '/v2/consumer_groups/%s/bindings/%s/%s/' % ('notagroup', REPO_ID, DISTRIBUTOR_ID)

        # Test
        call_status, call_body = self.delete(path)
        self.assertEqual(404, call_status)

    def test_unbinding(self):
        """
        Test pulp.server.webservices.controllers.consumer_groups.ConsumerGroupBindings.DELETE
        to confirm that when given valid arguments, the binding succeeds.
        """
        # Setup a binding to be deleted
        self.populate()
        path = '/v2/consumer_groups/%s/bindings/' % GROUP_ID
        params = {
            'repo_id': REPO_ID,
            'distributor_id': DISTRIBUTOR_ID
        }
        self.post(path, params)
        path = '/v2/consumer_groups/%s/bindings/%s/%s/' % (GROUP_ID, REPO_ID, DISTRIBUTOR_ID)

        # Test
        call_status, call_body = self.delete(path)
        self.assertEqual(202, call_status)
