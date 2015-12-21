from mock import Mock, patch, call

from pulp.streamer.config import load_configuration, DEFAULT_VALUES
from pulp.common.compat import unittest


class TestConfig(unittest.TestCase):

    @patch('pulp.streamer.config.SafeConfigParser')
    def test_load_configuration(self, mock_parser_class):
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        expected_sections = DEFAULT_VALUES.keys()

        load_configuration(['/a/file'])
        self.assertEqual(mock_parser.add_section.call_count, len(expected_sections))
        actual_sections = mock_parser.add_section.call_args_list
        for expected, actual in zip(expected_sections, actual_sections):
            self.assertEqual(call(expected), actual)
            for option, value in DEFAULT_VALUES[expected].items():
                self.assertIn(call(expected, option, value), mock_parser.set.call_args_list)
        mock_parser.read.assert_called_once_with(['/a/file'])
