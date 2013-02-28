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


from mock import patch, Mock

from base import ClientTests, Response

from pulp_node import constants
from pulp_node.extensions.admin.commands import *

# --- IDs --------------------------------------------------------------------

NODE_ID = 'test_node'
REPOSITORY_ID = 'test_repository'


# --- binding mocks ----------------------------------------------------------

REPO_ENABLED_CHECK = 'pulp_node.extensions.admin.commands.repository_enabled'
NODE_ACTIVATED_CHECK = 'pulp_node.extensions.admin.commands.node_activated'

CONSUMER_LIST_API = 'pulp.bindings.consumer.ConsumerAPI.consumers'
NODE_ACTIVATE_API = 'pulp.bindings.consumer.ConsumerAPI.update'
REPO_LIST_API = 'pulp.bindings.repository.RepositoryAPI.repositories'
DISTRIBUTORS_API = 'pulp.bindings.repository.RepositoryDistributorAPI.distributors'
PUBLISH_API = 'pulp.bindings.repository.RepositoryActionsAPI.publish'
REPO_ENABLE_API = 'pulp.bindings.repository.RepositoryDistributorAPI.create'
REPO_DISABLE_API = 'pulp.bindings.repository.RepositoryDistributorAPI.delete'
BIND_API = 'pulp.bindings.consumer.BindingsAPI.bind'
UNBIND_API = 'pulp.bindings.consumer.BindingsAPI.unbind'


# --- responses --------------------------------------------------------------

CONSUMERS_ONLY = [
    {'notes': {}}
]

CONSUMERS_AND_NODES = [
    {'notes': {}},
    {'notes': {constants.NODE_NOTE_KEY: True}}
]

ALL_REPOSITORIES = [{'id': REPOSITORY_ID}, ]

NON_NODES_DISTRIBUTORS_ONLY = [
    {'id': 1, 'distributor_type_id': 1},
    {'id': 2, 'distributor_type_id': 2},
]

MIXED_DISTRIBUTORS = [
    {'id': 1, 'distributor_type_id': 1},
    {'id': 2, 'distributor_type_id': 2},
    {'id': 3, 'distributor_type_id': constants.HTTP_DISTRIBUTOR},
    {'id': 4, 'distributor_type_id': constants.HTTP_DISTRIBUTOR},
]


# --- tests ------------------------------------------------------------------

class TestListCommands(ClientTests):

    @patch(CONSUMER_LIST_API, return_value=Response(200, CONSUMERS_ONLY))
    def test_list_nodes_no_nodes(self, mock_binding):
        # Test
        command = NodeListCommand(self.context)
        command.run(fields=None)
        # Verify
        mock_binding.assert_called_with(bindings=False, details=False)
        lines = self.recorder.lines
        self.assertEqual(len(lines), 4)
        self.assertTrue('Child Nodes' in lines[1])

    @patch(CONSUMER_LIST_API, return_value=Response(200, CONSUMERS_AND_NODES))
    def test_list_nodes_with_node(self, mock_binding):
        # Test
        command = NodeListCommand(self.context)
        command.run(fields=None)
        # Verify
        mock_binding.assert_called_with(bindings=False, details=False)
        lines = self.recorder.lines
        self.assertEqual(len(lines), 7)
        self.assertTrue(NODE_LIST_TITLE in lines[1])

    @patch(REPO_LIST_API, return_value=Response(200, ALL_REPOSITORIES))
    @patch(DISTRIBUTORS_API, return_value=Response(200, NON_NODES_DISTRIBUTORS_ONLY))
    def test_list_repos_disabled_only(self, mock_binding, *unused):
        # Test
        command = NodeListRepositoriesCommand(self.context)
        command.run(details=True)
        # Verify
        mock_binding.assert_called_with(REPOSITORY_ID)
        lines = self.recorder.lines
        self.assertEqual(len(lines), 4)
        self.assertTrue(REPO_LIST_TITLE in lines[1])

    @patch(REPO_LIST_API, return_value=Response(200, ALL_REPOSITORIES))
    @patch(DISTRIBUTORS_API, return_value=Response(200, MIXED_DISTRIBUTORS))
    def test_list_repos_with_enabled(self, mock_binding, *unused):
        # Test
        command = NodeListRepositoriesCommand(self.context)
        command.run(details=True)
        # Verify
        mock_binding.assert_called_with(REPOSITORY_ID)
        lines = self.recorder.lines
        self.assertEqual(len(lines), 9)
        self.assertTrue(REPO_LIST_TITLE in lines[1])


class TestPublishCommand(ClientTests):

    @patch('pulp.client.commands.polling.PollingCommand.postponed')
    @patch('pulp.client.commands.polling.PollingCommand.rejected')
    @patch('pulp.client.commands.polling.PollingCommand.process')
    @patch(PUBLISH_API, return_value=Response(200, {}))
    def test_publish(self, mock_binding, *unused):
        # Test
        command = NodeRepoPublishCommand(self.context)
        keywords = {OPTION_REPO_ID.keyword: REPOSITORY_ID}
        command.run(**keywords)
        # Verify
        mock_binding.assert_called_with(REPOSITORY_ID, constants.HTTP_DISTRIBUTOR, {})


class TestActivationCommands(ClientTests):

    @patch(NODE_ACTIVATE_API, return_value=Response(200, {}))
    def test_activate(self, mock_binding):
        # Test
        command = NodeActivateCommand(self.context)
        keywords = {OPTION_CONSUMER_ID.keyword: NODE_ID}
        command.run(**keywords)
        # Verify
        delta = {'notes':{constants.NODE_NOTE_KEY: True}}
        mock_binding.assert_called_with(NODE_ID, delta)

    @patch(NODE_ACTIVATED_CHECK, return_value=True)
    @patch(NODE_ACTIVATE_API, return_value=Response(200, {}))
    def test_deactivate(self, mock_binding, mock_activated):
        # Test
        command = NodeDeactivateCommand(self.context)
        keywords = {NODE_ID_OPTION.keyword: NODE_ID}
        command.run(**keywords)
        # Verify
        delta = {'notes':{constants.NODE_NOTE_KEY: None}}
        mock_activated.assert_called_with(self.context, NODE_ID)
        mock_binding.assert_called_with(NODE_ID, delta)

    @patch(NODE_ACTIVATED_CHECK, return_value=False)
    @patch(NODE_ACTIVATE_API, return_value=Response(200, {}))
    def test_deactivate_not_activated(self, mock_binding, mock_activated):
        # Test
        command = NodeDeactivateCommand(self.context)
        keywords = {NODE_ID_OPTION.keyword: NODE_ID}
        command.run(**keywords)
        # Verify
        mock_activated.assert_called_with(self.context, NODE_ID)
        self.assertFalse(mock_binding.called)


class TestEnableCommands(ClientTests):

    @patch(REPO_ENABLED_CHECK, return_value=False)
    @patch(REPO_ENABLE_API, return_value=(200, {}))
    def test_enable(self, mock_binding, *unused):
        # Test
        command = NodeRepoEnableCommand(self.context)
        keywords = {
            OPTION_REPO_ID.keyword: REPOSITORY_ID,
            AUTO_PUBLISH_OPTION.keyword: 'true',
        }
        command.run(**keywords)
        # Verify
        mock_binding.assert_called_with(REPOSITORY_ID,  constants.HTTP_DISTRIBUTOR, {},
                                        True, constants.HTTP_DISTRIBUTOR)

    @patch(REPO_ENABLED_CHECK, return_value=False)
    @patch(REPO_ENABLE_API, return_value=(200, {}))
    def test_enable_no_auto_publish(self, mock_binding, *unused):
        # Test
        command = NodeRepoEnableCommand(self.context)
        keywords = {
            OPTION_REPO_ID.keyword: REPOSITORY_ID,
            AUTO_PUBLISH_OPTION.keyword: 'false',
        }
        command.run(**keywords)
        # Verify
        mock_binding.assert_called_with(REPOSITORY_ID,  constants.HTTP_DISTRIBUTOR, {},
                                        False, constants.HTTP_DISTRIBUTOR)

    @patch(REPO_ENABLED_CHECK, return_value=True)
    @patch(REPO_ENABLE_API, return_value=(200, {}))
    def test_enable(self, mock_binding, *unused):
        # Test
        command = NodeRepoEnableCommand(self.context)
        keywords = {
            OPTION_REPO_ID.keyword: REPOSITORY_ID,
            AUTO_PUBLISH_OPTION.keyword: 'true',
            }
        command.run(**keywords)
        # Verify
        self.assertFalse(mock_binding.called)

    @patch('pulp_node.extensions.admin.commands.repository_enabled', return_value=True)
    @patch(REPO_DISABLE_API, return_value=(200, {}))
    def test_disable(self, mock_binding, *unused):
        # Test
        command = NodeRepoDisableCommand(self.context)
        keywords = {OPTION_REPO_ID.keyword: REPOSITORY_ID}
        command.run(**keywords)
        # Verify
        mock_binding.assert_called_with(REPOSITORY_ID,  constants.HTTP_DISTRIBUTOR)
        
        
class TestBindCommands(ClientTests):

    @patch(NODE_ACTIVATED_CHECK, return_value=True)
    @patch(BIND_API, return_value=Response(200, {}))
    def test_bind(self, mock_binding, *unused):
        # Test
        command = NodeBindCommand(self.context)
        keywords = {
            OPTION_REPO_ID.keyword: REPOSITORY_ID,
            NODE_ID_OPTION.keyword: NODE_ID,
            STRATEGY_OPTION.keyword: constants.DEFAULT_STRATEGY,
        }
        command.run(**keywords)
        # Verify
        mock_binding.assert_called_with(
            NODE_ID,
            REPOSITORY_ID,
            constants.HTTP_DISTRIBUTOR,
            notify_agent=False,
            binding_config={constants.STRATEGY_KEYWORD: constants.DEFAULT_STRATEGY})

    @patch(NODE_ACTIVATED_CHECK, return_value=True)
    @patch(BIND_API, return_value=Response(200, {}))
    def test_bind_with_strategy(self, mock_binding, *unused):
        # Test
        command = NodeBindCommand(self.context)
        keywords = {
            OPTION_REPO_ID.keyword: REPOSITORY_ID,
            NODE_ID_OPTION.keyword: NODE_ID,
            STRATEGY_OPTION.keyword: constants.MIRROR_STRATEGY,
        }
        command.run(**keywords)
        # Verify
        mock_binding.assert_called_with(
            NODE_ID,
            REPOSITORY_ID,
            constants.HTTP_DISTRIBUTOR,
            notify_agent=False,
            binding_config={constants.STRATEGY_KEYWORD: constants.MIRROR_STRATEGY})

    @patch(NODE_ACTIVATED_CHECK, return_value=False)
    @patch(BIND_API, return_value=Response(200, {}))
    def test_bind_not_activated(self, mock_binding, *unused):
        # Test
        command = NodeBindCommand(self.context)
        keywords = {
            OPTION_REPO_ID.keyword: REPOSITORY_ID,
            NODE_ID_OPTION.keyword: NODE_ID,
            STRATEGY_OPTION.keyword: constants.MIRROR_STRATEGY,
        }
        command.run(**keywords)
        # Verify
        self.assertFalse(mock_binding.called)

    @patch(NODE_ACTIVATED_CHECK, return_value=True)
    @patch(UNBIND_API, return_value=Response(200, {}))
    def test_unbind(self, mock_binding, *unused):
        # Test
        command = NodeUnbindCommand(self.context)
        keywords = {
            OPTION_REPO_ID.keyword: REPOSITORY_ID,
            NODE_ID_OPTION.keyword: NODE_ID,
        }
        command.run(**keywords)
        # Verify
        mock_binding.assert_called_with(NODE_ID, REPOSITORY_ID, constants.HTTP_DISTRIBUTOR)