# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Responsible for parsing and validating type descriptors.
"""

import logging
import operator
import re

from pulp.server.content.types import model
from pulp.server.compat import json

# -- constants ---------------------------------------------------------------

REQUIRED_DEFINITION_FIELDS = ['id', 'display_name', 'description', 'unit_key']
OPTIONAL_DEFINITION_FIELDS = ['search_indexes', 'referenced_types']

TYPE_ID_REGEX = re.compile(r'^[_A-Za-z]+$') # letters and underscore

LOG = logging.getLogger(__name__)

# -- syntax exceptions -------------------------------------------------------

class SyntaxException(Exception):
    """
    Base exception class for all syntax exceptions. Intended as a quick way
    for the caller to identify/react to any syntax error.

    All syntax exceptions have the potential to indicate more than one
    descriptor that failed the test.

    @param descriptors: list of descriptors that could not be parsed
    @type  descriptors: list of L{TypeDescriptor}
    """

    def __init__(self, descriptors):
        Exception.__init__(self)
        self.descriptors = descriptors

    def error_filenames(self):
        """
        @return: list of filenames for descriptors that caused the error
        @rtype:  list of str
        """
        return [d.filename for d in self.descriptors]

    def __str__(self):
        return 'Exception [%s] for files [%s]' % (self.__class__.__name__, ', '.join(self.error_filenames()))

class Unparsable(SyntaxException):
    """
    One or more descriptors could not be parsed.
    """
    pass

class MissingRoot(SyntaxException):
    """
    A descriptor does not contain the necessary root element.
    """
    pass

class InvalidAttribute(SyntaxException):
    """
    A type definition contains an unexpected attribute.
    """
    pass

class MissingAttribute(SyntaxException):
    """
    A type definition is missing a required attribute.
    """
    pass

# -- semantics exceptions ----------------------------------------------------

class SemanticsException(Exception):
    """
    Base exception class for all semantics exceptions. Intended as a quick way
    for the caller to identify/react to any semantics error.
    """
    pass

class InvalidTypeId(SemanticsException):
    """
    A descriptor contains a type definition with an invalid type ID.
    """

    def __init__(self, offending_type_ids):
        SemanticsException.__init__(self)
        self.type_ids = offending_type_ids

class DuplicateType(SemanticsException):
    """
    A type ID was reused either in a single descriptor or across multiple
    descriptors.
    """

    def __init__(self, duplicate_type_ids):
        SemanticsException.__init__(self)
        self.type_ids = duplicate_type_ids

class UndefinedReferencedIds(SemanticsException):
    """
    One or more referenced type definitions reference types that are not defined.
    """

    def __init__(self, missing_referenced_ids):
        SemanticsException.__init__(self)
        self.missing_referenced_ids = missing_referenced_ids

# -- public api --------------------------------------------------------------

def parse(descriptors):
    """
    Parses and validates the contents of the given descriptors. The parsed
    versions of the descriptors will be stored in the objects themselves,
    meaning the state of each object in the supplied list will change as
    part of this call.

    If there are any issues in resolving the type definitions contained
    within, the appropriate exception will be raised to indicate the
    offending descriptors.

    @param descriptors: set of all descriptors to be parsed by the Pulp server
    @type  descriptors: list of L{TypeDescriptor}
    """

    all_filenames = [d.filename for d in descriptors]
    LOG.info('Loading type descriptors [%s]' % ', '.join(all_filenames))

    LOG.info('Parsing type descriptors')
    _parse_descriptors(descriptors)

    LOG.info('Validating type descriptor syntactic integrity')
    _validate_syntax(descriptors)

    LOG.info('Validating type descriptor semantic integrity')
    _validate_semantics(descriptors)

    # If we got this far without an exception, the types are valid and can
    # be instantiated
    type_definitions = _instantiate_type_definitions(descriptors)

    return type_definitions

# -- parsing and validation --------------------------------------------------

def _parse_descriptors(descriptors):
    """
    Attempts to parse each descriptor. The parsed contents will be stored in each
    descriptor instance.

    @raises Unparsable: if one or more descriptors cannot be parsed
    """

    error_descriptors = []

    for parse_me in descriptors:
        try:
            parse_me.parsed = json.loads(parse_me.contents)
        except Exception:
            LOG.exception('Error parsing descriptor [%s]' % parse_me.filename)
            error_descriptors.append(parse_me)

    if len(error_descriptors) > 0:
        raise Unparsable(error_descriptors)

def _validate_syntax(descriptors):
    """
    Verifies that the all of the descriptors are syntactically valid, raising
    the appropriate exception if one or more is not.

    Exceptions are documented in the load() method to reduce duplication
    and since that is intended public API.

    @param descriptors: set of descriptors to validate
    @type  descriptors: list of L{TypeDescriptor}
    """

    # Verify each descriptor has the correct root element
    error_descriptors = [d for d in descriptors if not 'types' in d.parsed]

    if len(error_descriptors) > 0:
        raise MissingRoot(error_descriptors)

    # Type definition syntax
    invalid_attribute_descriptors = []
    missing_attribute_descriptors = []

    for d in descriptors:
        for type_definition in d.parsed['types']:

            # Make sure there are no foreign elements in each definition
            for key in type_definition.keys():
                if key not in REQUIRED_DEFINITION_FIELDS and key not in OPTIONAL_DEFINITION_FIELDS:
                    LOG.error('Unexpected key [%s] from descriptor [%s] in type definition [%s]' % (key, d.filename, ', '.join(type_definition.keys())))
                    invalid_attribute_descriptors.append(d)

            # Make sure all required fields are present
            for key in REQUIRED_DEFINITION_FIELDS:
                if key not in type_definition:
                    LOG.error('Unexpected key [%s] from descriptor [%s] in type definition [%s]' % (key, d.filename, ', '.join(type_definition.keys())))
                    missing_attribute_descriptors.append(d)

    if len(invalid_attribute_descriptors) > 0:
        raise InvalidAttribute(invalid_attribute_descriptors)

    if len(missing_attribute_descriptors) > 0:
        raise MissingAttribute(missing_attribute_descriptors)

def _validate_semantics(descriptors):
    """
    Verifies that the set of descriptors are semantically valid, raising
    the appropriate exception if one or more is not.

    Exceptions are documented in the load() method to reduce duplication
    and since that is intended public API.

    @param descriptors: set of descriptors to validate
    @type  descriptors: list of L{TypeDescriptor}
    """

    all_type_ids = _all_type_ids(descriptors)

    # Type ID validtity
    error_ids = [id for id in all_type_ids if not _valid_id(id)]

    if len(error_ids) > 0:
        raise InvalidTypeId(error_ids)

    # Duplicates
    all_copy = list(all_type_ids)
    unique_ids = set(all_type_ids)

    for id in unique_ids:
        all_copy.remove(id)

    if len(all_copy) > 0: # remaining IDs were duplicated
        raise DuplicateType(all_copy)

    # Ensure referenced referenced types are defined as types on their own
    all_referenced_ids = _all_referenced_type_ids(descriptors)
    undefined_referenced_ids = all_referenced_ids - set(all_type_ids)

    if len(undefined_referenced_ids) > 0:
        raise UndefinedReferencedIds(undefined_referenced_ids)

def _instantiate_type_definitions(descriptors):
    """
    Once the descriptors have been validated, this call creates objects
    to represent each type definition.

    @param descriptors: descriptors containing type definitions
    @type  descriptors: list of L{TypeDescriptor}

    @return: list of all type definitions across all descriptors
    @rtype:  list of L{TypeDefinition}
    """

    all_type_dicts = _all_types(descriptors)
    all_types = []

    for type_dict in all_type_dicts:

        # Handle optional values
        search_indexes = type_dict.get('search_indexes', [])
        referenced_types = type_dict.get('referenced_types', [])

        type_def = model.TypeDefinition(type_dict['id'], type_dict['display_name'],
                                        type_dict['description'], type_dict['unit_key'],
                                        search_indexes, referenced_types)
        all_types.append(type_def)

    return all_types

# -- utility -----------------------------------------------------------------

def _all_types(descriptors):
    """
    @return: list of type dicts for all types in each descriptor
    @rtype:  list of dict
    """
    if not descriptors:
        return []
    return reduce(operator.add, [descriptor.parsed['types'] for descriptor in descriptors])

def _all_type_ids(descriptors):
    """
    @return: list of all type IDs across all descriptors (potentially containing
             duplicates)
    @rtype:  list of str
    """
    types = _all_types(descriptors)
    all_ids = [type['id'] for type in types]

    return all_ids

def _all_referenced_type_ids(descriptors):
    """
    @return: list of all IDs that are mentioned as referenced types across all types
             in every descriptor
    @rtype:  set of str
    """
    types = _all_types(descriptors)
    all_referenced_ids = set()
    for referenced_ids in [t['referenced_types'] for t in types if 'referenced_types' in t]:
        if not isinstance(referenced_ids, list):
            referenced_ids = [referenced_ids]

        all_referenced_ids .update(referenced_ids)

    return all_referenced_ids

def _valid_id(id):
    """
    @return: True if the given ID is a valid type ID; false otherwise
    """
    return TYPE_ID_REGEX.match(id) is not None