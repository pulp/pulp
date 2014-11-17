import mock

from ... import base
from pulp.plugins.loader import api
from pulp.plugins.types.model import TypeDefinition


class LoaderApiTests(base.PulpServerTests):
    """
    This class tests the pulp.plugins.loader.api module.
    """

    @mock.patch('pulp.plugins.loader.api._load_type_definitions', autospec=True)
    @mock.patch('pulp.plugins.loader.api._check_content_definitions', autospec=True)
    def test_load_content_types_dry_run(self, mock_check_content, mock_load_type):
        """
        Test that calling load_content_types with dry_run=True results in checking the content types
         rather than loading them.
        """
        api.load_content_types(dry_run=True)
        self.assertEquals(1, mock_check_content.call_count)
        self.assertEquals(0, mock_load_type.call_count)

    @mock.patch('pulp.plugins.types.parser.parse', autospec=True)
    @mock.patch('pulp.plugins.types.database.type_definition', autospec=True)
    def test_check_content_definitions_nothing_old(self, mock_type_definition, mock_parser):
        """
        Test that when the content type from the database matches the TypeDefinition,
        an empty list is returned.
        """
        fake_type = {
            'id': 'steve_holt',
            'display_name': 'STEVE HOLT!',
            'description': 'STEVE HOLT!',
            'unit_key': ['STEVE HOLT!'],
            'search_indexes': ['STEVE HOLT!'],
            'referenced_types': ['STEVE HOLT!'],
        }
        mock_type_definition.return_value = fake_type
        type_definition = TypeDefinition('steve_holt', 'STEVE HOLT!', 'STEVE HOLT!', 'STEVE HOLT!',
                                         'STEVE HOLT!', 'STEVE HOLT!')
        mock_parser.return_value = [type_definition]

        result = api._check_content_definitions([])
        self.assertEquals(0, len(result))

    @mock.patch('pulp.plugins.types.parser.parse', autospec=True)
    @mock.patch('pulp.plugins.types.database.type_definition', autospec=True)
    def test_check_content_definitions_old(self, mock_type_definition, mock_parser):
        """
        Test that when the content type from the database doesn't match the TypeDefinition,
        the list contains that content type.
        """
        fake_type = {
            'id': 'gob',
            'display_name': 'Trickster',
            'description': 'Trickster',
            'unit_key': ['Trickster'],
            'search_indexes': ['Trickster'],
            'referenced_types': ['Trickster'],
        }
        mock_type_definition.return_value = fake_type
        type_definition = TypeDefinition('gob', 'STEVE HOLT!', 'STEVE HOLT!', 'STEVE HOLT!',
                                         'STEVE HOLT!', 'STEVE HOLT!')
        mock_parser.return_value = [type_definition]

        result = api._check_content_definitions([])
        self.assertEquals(1, len(result))
        self.assertEquals(result[0], type_definition)