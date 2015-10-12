from mock import patch

from base import ClientTests, Response

from pulp_node import constants
from pulp_node.extensions.consumer import commands


NODE_ID = 'test_node'
REPOSITORY_ID = 'test_repository'


LOAD_CONSUMER_API = 'pulp_node.extensions.consumer.commands.load_consumer_id'
NODE_ACTIVATED_CHECK = 'pulp_node.extensions.consumer.commands.node_activated'

NODE_ACTIVATE_API = 'pulp.bindings.consumer.ConsumerAPI.update'
BIND_API = 'pulp.bindings.consumer.BindingsAPI.bind'
UNBIND_API = 'pulp.bindings.consumer.BindingsAPI.unbind'


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


class TestActivationCommands(ClientTests):

    @patch(NODE_ACTIVATED_CHECK, return_value=False)
    @patch(LOAD_CONSUMER_API, return_value=NODE_ID)
    @patch(NODE_ACTIVATE_API, return_value=Response(200, {}))
    def test_activate(self, mock_binding, *unused):
        # Test
        command = commands.NodeActivateCommand(self.context)
        keywords = {commands.STRATEGY_OPTION.keyword: constants.DEFAULT_STRATEGY}
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
        command = commands.NodeActivateCommand(self.context)
        keywords = {commands.STRATEGY_OPTION.keyword: constants.DEFAULT_STRATEGY}
        command.run(**keywords)
        # Verify
        self.assertFalse(mock_binding.called)

    @patch(LOAD_CONSUMER_API, return_value=NODE_ID)
    @patch(NODE_ACTIVATED_CHECK, return_value=True)
    @patch(NODE_ACTIVATE_API, return_value=Response(200, {}))
    def test_deactivate(self, mock_binding, mock_activated, *unused):
        # Test
        command = commands.NodeDeactivateCommand(self.context)
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
        command = commands.NodeDeactivateCommand(self.context)
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
        command = commands.NodeBindCommand(self.context)
        keywords = {
            commands.OPTION_REPO_ID.keyword: REPOSITORY_ID,
            commands.STRATEGY_OPTION.keyword: constants.DEFAULT_STRATEGY,
        }
        command.run(**keywords)
        # Verify
        self.assertTrue(commands.OPTION_REPO_ID in command.options)
        self.assertTrue(commands.STRATEGY_OPTION in command.options)
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
        command = commands.NodeBindCommand(self.context)
        keywords = {
            commands.OPTION_REPO_ID.keyword: REPOSITORY_ID,
            commands.STRATEGY_OPTION.keyword: constants.MIRROR_STRATEGY,
        }
        command.run(**keywords)
        # Verify
        self.assertTrue(commands.OPTION_REPO_ID in command.options)
        self.assertTrue(commands.STRATEGY_OPTION in command.options)
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
        command = commands.NodeBindCommand(self.context)
        keywords = {
            commands.OPTION_REPO_ID.keyword: REPOSITORY_ID,
            commands.STRATEGY_OPTION.keyword: constants.MIRROR_STRATEGY,
        }
        command.run(**keywords)
        # Verify
        self.assertTrue(commands.OPTION_REPO_ID in command.options)
        self.assertTrue(commands.STRATEGY_OPTION in command.options)
        self.assertFalse(mock_binding.called)

    @patch(LOAD_CONSUMER_API, return_value=NODE_ID)
    @patch(NODE_ACTIVATED_CHECK, return_value=True)
    @patch(UNBIND_API, return_value=Response(200, {}))
    def test_unbind(self, mock_binding, *unused):
        # Test
        command = commands.NodeUnbindCommand(self.context)
        keywords = {commands.OPTION_REPO_ID.keyword: REPOSITORY_ID}
        command.run(**keywords)
        # Verify
        self.assertTrue(commands.OPTION_REPO_ID in command.options)
        mock_binding.assert_called_with(NODE_ID, REPOSITORY_ID, constants.HTTP_DISTRIBUTOR)
