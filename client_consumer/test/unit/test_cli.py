import unittest

import mock

from pulp.client.consumer import cli


class TestWriteToLocation(unittest.TestCase):
    """
    Tests for writing content to a file.
    """

    @mock.patch('pulp.client.consumer.cli.os')
    @mock.patch('__builtin__.open', new_callable=mock.MagicMock())
    def test_dir_struct_exists(self, mopen, mock_os):
        """
        Test that when the directory structure already exists, the write still happens.
        """

        class MockException(OSError):
            pass

        mock_e = MockException()
        mock_e.errno = 17
        mock_os.makedirs.side_effect = mock_e
        mock_fp = open.return_value

        cli.write_to_location('test/loc', 'content')
        mock_os.path.dirname.assert_called_once_with('test/loc')
        mock_os.makedirs.assert_called_once_with(mock_os.path.dirname.return_value)
        open.assert_called_once_with('test/loc', 'w+')
        mock_fp.write.assert_called_once_with('content')
        mock_fp.close.assert_called_once_with()

    @mock.patch('pulp.client.consumer.cli.os')
    @mock.patch('__builtin__.open', new_callable=mock.MagicMock())
    def test_misc_os_err(self, mopen, mock_os):
        """
        Test that misc errors are reraised and the write does not happen.
        """

        class MockException(OSError):
            pass

        mock_e = MockException()
        mock_e.errno = 16
        mock_os.makedirs.side_effect = mock_e
        mock_fp = open.return_value

        self.assertRaises(MockException, cli.write_to_location, 'test/loc', 'content')
        self.assertEqual(mock_fp.write.call_count, 0)

    @mock.patch('pulp.client.consumer.cli.os')
    @mock.patch('__builtin__.open', new_callable=mock.MagicMock())
    def test_write_err(self, *_):
        """
        If there is a problem with the write, the file is still closed.
        """

        class MockException(Exception):
            pass

        mock_fp = open.return_value
        mock_fp.write.side_effect = MockException
        self.assertRaises(MockException, cli.write_to_location, 'test/loc', 'content')
        mock_fp.write.assert_called_once_with('content')
        mock_fp.close.assert_called_once_with()

    @mock.patch('pulp.client.consumer.cli.os')
    @mock.patch('__builtin__.open', new_callable=mock.MagicMock())
    def test_as_expected(self, mopen, mock_os):
        """
        When everything works as expected, ensure that the file is closed.
        """
        mock_fp = open.return_value
        cli.write_to_location('test/loc', 'content')
        mock_os.path.dirname.assert_called_once_with('test/loc')
        mock_os.makedirs.assert_called_once_with(mock_os.path.dirname.return_value)
        open.assert_called_once_with('test/loc', 'w+')
        mock_fp.write.assert_called_once_with('content')
        mock_fp.close.assert_called_once_with()


class TestUpdateServerKey(unittest.TestCase):
    """
    Tests for updating the server key.
    """

    @mock.patch('pulp.client.consumer.cli.write_to_location')
    def test_as_expected(self, mock_write):
        """
        Everything is as expected, content is written to the location in the config file.
        """
        mock_cmd = mock.MagicMock()
        key_response = mock_cmd.context.server.static.get_server_key.return_value
        key_loc = mock_cmd.context.config['getter']['getter']
        cli.update_server_key(mock_cmd)
        mock_write.assert_called_once_with(key_loc, key_response.response_body)

    @mock.patch('pulp.client.consumer.cli.write_to_location')
    def test_binding_exception(self, mock_write):
        """
        If there is a problem getting the key, do not attempt to write the file.
        """

        class MockException(Exception):

            def __str__(self):
                return "Mock Exception str"

        mock_cmd = mock.MagicMock()
        mock_cmd.context.server.static.get_server_key.side_effect = MockException()
        cli.update_server_key(mock_cmd)
        msg = 'Download server RSA key failed [Mock Exception str]'
        mock_cmd.prompt.render_failure_message.assert_called_once_with(msg)
        self.assertEqual(mock_write.call_count, 0)
