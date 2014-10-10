import unittest

from mock import patch, Mock

from pulp.server import initialization as init_module
from pulp.server.initialization import InitializationException, initialize


INITIALIZATION_MODULE = 'pulp.server.initialization'


class TestInitializationException(unittest.TestCase):

    def test_initialization_exception_is_an_Exception(self):
        self.assertTrue(isinstance(InitializationException('foo'), BaseException))

    def test_initialization_exception_saves_message(self):
        mock_message = Mock()
        new_exc = InitializationException(mock_message)
        self.assertTrue(new_exc.message is mock_message)


class TestInitialize(unittest.TestCase):

    def setUp(self):
        self.patch_db_connection = patch(INITIALIZATION_MODULE + '.db_connection')
        self.mock_db_connection = self.patch_db_connection.start()

        self.patch_plugin_api = patch(INITIALIZATION_MODULE + '.plugin_api')
        self.mock_plugin_api = self.patch_plugin_api.start()

        self.patch_manager_factory = patch(INITIALIZATION_MODULE + '.manager_factory')
        self.mock_manager_factory = self.patch_manager_factory.start()

        self.patch__IS_INITIALIZED = patch(INITIALIZATION_MODULE + '._IS_INITIALIZED', False)
        self.mock__IS_INITIALIZED = self.patch__IS_INITIALIZED.start()

    def tearDown(self):
        self.patch_db_connection.stop()
        self.patch_plugin_api.stop()
        self.patch_manager_factory.stop()
        self.patch__IS_INITIALIZED.stop()

    def test_initialize_only_does_nothing_if__IS_INITIALIZED_is_True(self):
        self.mock__IS_INITIALIZED = True
        initialize()
        self.assertTrue(not self.mock_db_connection.called)

    def test_initialize_calls_plugin_api_initialize(self):
        initialize()
        self.mock_plugin_api.initialize.assert_called_once_with()

    def test_initialize_does_not_call_manager_factory_if_plugin_api_raises_Exception(self):
        self.mock_plugin_api.initialize.side_effect = OSError('my message')
        try:
            initialize()
        except Exception:
            pass
        self.assertTrue(not self.mock_manager_factory.called)

    def test_initialize_calls_manager_factory(self):
        initialize()
        self.mock_manager_factory.initialize.assert_called_once_with()

    def test_global__IS_INITIALIZED_is_set_to_True(self):
        initialize()
        self.assertTrue(init_module._IS_INITIALIZED)
