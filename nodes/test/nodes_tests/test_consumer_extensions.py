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


from mock import patch

from base import ClientTests, Response

from pulp_node import constants
from pulp_node.extensions.consumer.commands import *


# --- IDs --------------------------------------------------------------------

NODE_ID = 'test_node'
REPOSITORY_ID = 'test_repository'


# --- binding mocks ----------------------------------------------------------

LOAD_CONSUMER_API = 'pulp_node.extensions.consumer.commands.load_consumer_id'
NODE_ACTIVATED_CHECK = 'pulp_node.extensions.consumer.commands.node_activated'

NODE_ACTIVATE_API = 'pulp.bindings.consumer.ConsumerAPI.update'
BIND_API = 'pulp.bindings.consumer.BindingsAPI.bind'
UNBIND_API = 'pulp.bindings.consumer.BindingsAPI.unbind'


# --- responses --------------------------------------------------------------


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


class TestActivationCommands(ClientTests):

    @patch(NODE_ACTIVATED_CHECK, return_value=False)
    @patch(LOAD_CONSUMER_API, return_value=NODE_ID)
    @patch(NODE_ACTIVATE_API, return_value=Response(200, {}))
    def test_activate(self, mock_binding, *unused):
        # Test
        command = NodeActivateCommand(self.context)
        keywords = {STRATEGY_OPTION.keyword: constants.DEFAULT_STRATEGY}
        command.run(**keywords)
        # Verify
        delta = {
            'notes': {
                constants.NODE_NOTE_KEY: True,
                constants.STRATEGY_NOTE_KEY: constants.DEFAULT_STRATEGY
            }
        }
        mock_binding.assert_called_with(NODE_ID, delta)

    @patch(NODE_ACTIVATED_CHECK, return_value=True)
    @patch(LOAD_CONSUMER_API, return_value=NODE_ID)
    @patch(NODE_ACTIVATE_API, return_value=Response(200, {}))
    def test_activate_already_activated(self, mock_binding, *unused):
        command = NodeActivateCommand(self.context)
        keywords = {STRATEGY_OPTION.keyword: constants.DEFAULT_STRATEGY}
        command.run(**keywords)
        # Verify
        self.assertFalse(mock_binding.called)

    @patch(LOAD_CONSUMER_API, return_value=NODE_ID)
    @patch(NODE_ACTIVATED_CHECK, return_value=True)
    @patch(NODE_ACTIVATE_API, return_value=Response(200, {}))
    def test_deactivate(self, mock_binding, mock_activated, *unused):
        # Test
        command = NodeDeactivateCommand(self.context)
        command.run()
        # Verify
        delta = {
            'notes': {
                constants.NODE_NOTE_KEY: None,
                constants.STRATEGY_NOTE_KEY: None
            }
        }
        mock_activated.assert_called_with(self.context, NODE_ID)
        mock_binding.assert_called_with(NODE_ID, delta)

    @patch(LOAD_CONSUMER_API, return_value=NODE_ID)
    @patch(NODE_ACTIVATED_CHECK, return_value=False)
    @patch(NODE_ACTIVATE_API, return_value=Response(200, {}))
    def test_deactivate_not_activated(self, mock_binding, mock_activated, *unused):
        # Test
        command = NodeDeactivateCommand(self.context)
        command.run()
        # Verify
        mock_activated.assert_called_with(self.context, NODE_ID)
        self.assertFalse(mock_binding.called)

        
class TestBindCommands(ClientTests):

    @patch(LOAD_CONSUMER_API, return_value=NODE_ID)
    @patch(NODE_ACTIVATED_CHECK, return_value=True)
    @patch(BIND_API, return_value=Response(200, {}))
    def test_bind(self, mock_binding, *unused):
        # Test
        command = NodeBindCommand(self.context)
        keywords = {
            OPTION_REPO_ID.keyword: REPOSITORY_ID,
            STRATEGY_OPTION.keyword: constants.DEFAULT_STRATEGY,
        }
        command.run(**keywords)
        # Verify
        self.assertTrue(OPTION_REPO_ID in command.options)
        self.assertTrue(STRATEGY_OPTION in command.options)
        mock_binding.assert_called_with(
            NODE_ID,
            REPOSITORY_ID,
            constants.HTTP_DISTRIBUTOR,
            notify_agent=False,
            binding_config={constants.STRATEGY_KEYWORD: constants.DEFAULT_STRATEGY})

    @patch(LOAD_CONSUMER_API, return_value=NODE_ID)
    @patch(NODE_ACTIVATED_CHECK, return_value=True)
    @patch(BIND_API, return_value=Response(200, {}))
    def test_bind_with_strategy(self, mock_binding, *unused):
        # Test
        command = NodeBindCommand(self.context)
        keywords = {
            OPTION_REPO_ID.keyword: REPOSITORY_ID,
            STRATEGY_OPTION.keyword: constants.MIRROR_STRATEGY,
        }
        command.run(**keywords)
        # Verify
        self.assertTrue(OPTION_REPO_ID in command.options)
        self.assertTrue(STRATEGY_OPTION in command.options)
        mock_binding.assert_called_with(
            NODE_ID,
            REPOSITORY_ID,
            constants.HTTP_DISTRIBUTOR,
            notify_agent=False,
            binding_config={constants.STRATEGY_KEYWORD: constants.MIRROR_STRATEGY})

    @patch(LOAD_CONSUMER_API, return_value=NODE_ID)
    @patch(NODE_ACTIVATED_CHECK, return_value=False)
    @patch(BIND_API, return_value=Response(200, {}))
    def test_bind_not_activated(self, mock_binding, *unused):
        # Test
        command = NodeBindCommand(self.context)
        keywords = {
            OPTION_REPO_ID.keyword: REPOSITORY_ID,
            STRATEGY_OPTION.keyword: constants.MIRROR_STRATEGY,
        }
        command.run(**keywords)
        # Verify
        self.assertTrue(OPTION_REPO_ID in command.options)
        self.assertTrue(STRATEGY_OPTION in command.options)
        self.assertFalse(mock_binding.called)

    @patch(LOAD_CONSUMER_API, return_value=NODE_ID)
    @patch(NODE_ACTIVATED_CHECK, return_value=True)
    @patch(UNBIND_API, return_value=Response(200, {}))
    def test_unbind(self, mock_binding, *unused):
        # Test
        command = NodeUnbindCommand(self.context)
        keywords = {OPTION_REPO_ID.keyword: REPOSITORY_ID}
        command.run(**keywords)
        # Verify
        self.assertTrue(OPTION_REPO_ID in command.options)
        mock_binding.assert_called_with(NODE_ID, REPOSITORY_ID, constants.HTTP_DISTRIBUTOR)