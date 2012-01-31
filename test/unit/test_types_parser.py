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

# Python
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.server.content.types import parser, model

# -- test data ---------------------------------------------------------------

VALID_DESCRIPTOR_1 = model.TypeDescriptor('valid_descriptor_1',
"""{"types": [
    {"id" : "rpm",
     "display_name" : "RPM",
     "description" : "Yum RPM package",
     "unit_key" : ["name", "version", "release", "arch", "filename", "checksum"],
     "search_indexes" : [
         ["name", "epoch", "version", "release", "arch"],
         "filename"
     ]}
   ]}
""")

VALID_DESCRIPTOR_2 = model.TypeDescriptor('valid_descriptor_2',
"""{"types": [
    {"id" : "deb",
     "display_name" : "DEB",
     "description" : "Debian package",
     "unit_key" : "name",
     "search_indexes" : [
         ["name", "filename"], "filename"
     ]}
   ]}
""")

MULTI_TYPE_DESCRIPTOR = model.TypeDescriptor('multi_descriptor',
"""{"types": [
    {"id" : "rpm", "display_name" : "RPM", "description" : "RPM",
     "unit_key" : "name", "search_indexes" : "name"},
    {"id" : "deb", "display_name" : "DEB", "description" : "DEB",
     "unit_key" : "name", "search_indexes" : "name"}
   ]}
""")

CHILD_TYPES_DESCRIPTOR = model.TypeDescriptor('child_descriptor',
"""{"types": [
    {"id" : "aaa", "display_name" : "A", "description" : "A", "unit_key" : "name",
     "referenced_types" : ["ccc"]},
    {"id" : "bbb", "display_name" : "B", "description" : "B", "unit_key" : "name",
     "referenced_types" : "ccc"},
    {"id" : "ccc", "display_name" : "C", "description" : "C", "unit_key" : "name"}
   ]}
""")

BAD_CHILD_TYPES_DESCRIPTOR = model.TypeDescriptor('bad_children',
"""{"types": [
    {"id" : "a", "display_name" : "A", "description" : "A", "unit_key" : "name", "referenced_types" : ["not_there"]}
   ]}
""")

# -- test cases --------------------------------------------------------------

class ParserTest(testutil.PulpTest):

    def clean(self):
        super(ParserTest, self).clean()

        # Reset to the pre-parsed state
        VALID_DESCRIPTOR_1.parsed = None
        VALID_DESCRIPTOR_2.parsed = None
        MULTI_TYPE_DESCRIPTOR.parsed = None
        CHILD_TYPES_DESCRIPTOR.parsed = None
        BAD_CHILD_TYPES_DESCRIPTOR.parsed = None

    # -- parse tests ----------------------------------------------------------

    def test_parse_single_descriptor_single_type(self):
        """
        Tests the simple success case of loading multiple descriptors with
        valid data.
        """

        # Test
        definitions = parser.parse([VALID_DESCRIPTOR_1])

        # Verify
        self.assertTrue(definitions is not None)
        self.assertEqual(1, len(definitions))

        type_def = definitions[0]

        self.assertEqual('rpm', type_def.id)
        self.assertEqual('RPM', type_def.display_name)

        self.assertEqual(["name", "version", "release", "arch", "filename", "checksum"], type_def.unit_key)

        self.assertEqual(2, len(type_def.search_indexes))
        self.assertEqual(["name", "epoch", "version", "release", "arch"], type_def.search_indexes[0])
        self.assertEqual("filename", type_def.search_indexes[1])

    def test_parse_multiple_descriptors(self):
        """
        Tests parsing multiple descriptors.
        """

        # Test
        definitions = parser.parse([VALID_DESCRIPTOR_1, VALID_DESCRIPTOR_2])

        # Verify
        self.assertTrue(definitions is not None)
        self.assertEqual(2, len(definitions))

        self.assertEqual('rpm', definitions[0].id)
        self.assertEqual('deb', definitions[1].id)

    def test_parse_multiple_types(self):
        """
        Tests parsing a descriptor that contains multiple type definitions.
        """

        # Test
        definitions = parser.parse([MULTI_TYPE_DESCRIPTOR])

        # Verify
        self.assertTrue(definitions is not None)
        self.assertEqual(2, len(definitions))

        self.assertEqual('rpm', definitions[0].id)
        self.assertEqual('deb', definitions[1].id)

    def test_parse_with_children(self):
        """
        Tests parsing a descriptor with valid children definitions.
        """

        # Test
        definitions = parser.parse([CHILD_TYPES_DESCRIPTOR])

        # Verify
        self.assertTrue(definitions is not None)
        self.assertEqual(3, len(definitions))

        aaa_def = [d for d in definitions if d.id == 'aaa'][0]
        self.assertEqual(1, len(aaa_def.referenced_types))
        self.assertTrue('ccc' in aaa_def.referenced_types)

        bbb_def = [d for d in definitions if d.id == 'bbb'][0]
        self.assertEqual(1, len(bbb_def.referenced_types))
        self.assertTrue('ccc' in bbb_def.referenced_types)

        ccc_def = [d for d in definitions if d.id == 'ccc'][0]
        self.assertEqual(0, len(ccc_def.referenced_types))
        
    def test_parse_invalid_descriptor(self):
        """
        Tests the proper exception is thrown when a descriptor cannot be parsed.
        A valid descriptor is passed to show that at least one failed descriptor
        causes the parse to fail.
        """

        # Setup
        invalid = model.TypeDescriptor('invalid', 'foo')

        # Test
        try:
            parser.parse([VALID_DESCRIPTOR_1, invalid])
            self.fail('Exception not correctly thrown')
        except parser.Unparsable, e:
            self.assertEqual(1, len(e.error_filenames()))
            self.assertEqual('invalid', e.error_filenames()[0])
            e.__str__() # included just for coverage

    def test_parse_invalid_root(self):
        """
        Tests that a parsable but ill-formed descriptor throws the correct error.
        A valid descriptor is passed to show that at least one failed descriptor
        causes the parse to fail.
        """

        # Setup
        incorrect = model.TypeDescriptor('incorrect', '{"not-types" : "foo"}')

        # Test
        try:
            parser.parse([VALID_DESCRIPTOR_1, incorrect])
            self.fail('Exception not correctly thrown')
        except parser.MissingRoot, e:
            self.assertEqual(1, len(e.error_filenames()))
            self.assertEqual('incorrect', e.error_filenames()[0])
        
    def test_parse_extra_attribute(self):
        """
        Tests a type definition with unexpected attributes cannot be parsed.
        """

        # Setup
        extra = model.TypeDescriptor('extra',
            """{"types": [
                {"id" : "rpm", "display_name" : "RPM", "description" : "RPM",
                 "unit_key" : "name", "search_indexes" : "name",
                 "unexpected_attribute" : "foo"}
               ]}"""
        )

        # Test
        try:
            parser.parse([VALID_DESCRIPTOR_1, extra])
            self.fail('Exception not correctly thrown')
        except parser.InvalidAttribute, e:
            self.assertEqual(1, len(e.error_filenames()))
            self.assertEqual('extra', e.error_filenames()[0])

    def test_parse_missing_attribute(self):
        """
        Tests a type definition with a missing attribute cannot be parsed.
        """

        # Setup
        no_id = model.TypeDescriptor('no_id',
            """{"types": [
                {"display_name" : "RPM", "description" : "RPM",
                 "unit_key" : "name", "search_indexes" : "name"}
               ]}"""
        )

        # Test
        try:
            parser.parse([VALID_DESCRIPTOR_1, no_id])
            self.fail('Exception not correctly thrown')
        except parser.MissingAttribute, e:
            self.assertEqual(1, len(e.error_filenames()))
            self.assertEqual('no_id', e.error_filenames()[0])

    def test_parse_invalid_type_id(self):
        """
        Tests that a type definition with a malformed ID throws the correct
        error.
        """

        # Setup
        bad_id = model.TypeDescriptor('bad_id',
            """{"types": [
                {"id" : "bad-id", "display_name" : "RPM", "description" : "RPM",
                 "unit_key" : "name", "search_indexes" : "name"}
               ]}"""
        )

        # Test
        try:
            parser.parse([VALID_DESCRIPTOR_1, bad_id])
            self.fail('Exception not correctly thrown')
        except parser.InvalidTypeId, e:
            self.assertEqual(1, len(e.type_ids))
            self.assertEqual('bad-id', e.type_ids[0])
        
    def test_parse_duplicate_type(self):
        """
        Tests two types with the same ID throw the correct error.
        """

        # Test
        try:
            parser.parse([VALID_DESCRIPTOR_1, VALID_DESCRIPTOR_1])
            self.fail('Exception not correctly thrown')
        except parser.DuplicateType, e:
            self.assertEqual(1, len(e.type_ids))
            self.assertEqual('rpm', e.type_ids[0])

    def test_parse_bad_children(self):
        """
        Tests the correct error is raised when a type definition has undefined child IDs referenced.
        """

        # Test
        try:
            parser.parse([BAD_CHILD_TYPES_DESCRIPTOR])
            self.fail('Bad children did not raise an exception')
        except parser.UndefinedReferencedIds, e:
            self.assertEqual(1, len(e.missing_referenced_ids))
            self.assertTrue('not_there' in e.missing_referenced_ids)

    # -- utility tests --------------------------------------------------------

    def test_all_child_type_ids(self):
        """
        Tests retrieving all child type IDs for all types.
        """

        # Test
        parser._parse_descriptors([CHILD_TYPES_DESCRIPTOR])
        child_ids = parser._all_referenced_type_ids([CHILD_TYPES_DESCRIPTOR])

        # Verify
        self.assertEqual(1, len(child_ids))
        self.assertTrue('ccc' in child_ids)

    def test_valid_id(self):
        """
        Tests the type ID validity test.
        """

        # Test
        self.assertTrue(parser._valid_id('good'))
        self.assertTrue(parser._valid_id('Good'))
        self.assertTrue(not parser._valid_id('bad1'))
        self.assertTrue(not parser._valid_id('bad-'))
        self.assertTrue(not parser._valid_id('bad!'))