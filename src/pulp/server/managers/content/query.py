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

import os
from gettext import gettext as _
from pprint import pformat

from pulp.server.constants import LOCAL_STORAGE
from pulp.server.content.types import database as content_types_db
from pulp.server.exceptions import InvalidValue, MissingResource

class ContentQueryManager(object):
    """
    Query operations for content types and and individual content units.
    """

    def list_content_types(self):
        """
        List the currently defined content type ids.
        @retun: list of content type ids
        @rtype: list [str, ...]
        """
        return content_types_db.all_type_ids()

    def get_content_type(self, type_id):
        """
        """
        return content_types_db.type_definition(type_id)

    def list_content_units(self,
                           content_type,
                           db_spec=None,
                           model_fields=None,
                           start=0,
                           limit=None):
        """
        List the content units in a content type collection.
        @param content_type: unique id of content collection
        @type content_type: str
        @param db_spec: spec document used to filter the results,
                        None means no filter
        @type db_spec: None or dict
        @param model_fields: fields of each content unit to report,
                             None means all fields
        @type model_fields: None or list of str's
        @param start: offset from the beginning of the results to return as the
                      first element
        @type start: non-negative int
        @param limit: the maximum number of results to return,
                      None means no limit
        @type limit: None or non-negative int
        @return: list of content units in the content type collection that
                 matches the parameters
        @rtype: (possibly empty) tuple of dicts
        """
        collection = content_types_db.type_units_collection(content_type)
        if db_spec is None:
            db_spec = {}
        cursor = collection.find(db_spec, fields=model_fields)
        if start > 0:
            cursor.skip(start)
        if limit is not None:
            cursor.limit(limit)
        return tuple(cursor)

    def get_content_unit_by_keys_dict(self, content_type, unit_keys_dict, model_fields=None):
        """
        Look up an individual content unit in the corresponding content type
        collection using the given keys dictionary.
        @param content_type: unique id of content collection
        @type content_type: str
        @param unit_keys_dict: dictionary of key, value pairs that can uniquely
                               identify a content unit
        @type unit_keys_dict: dict
        @param model_fields: fields of each content unit to report,
                             None means all fields
        @type model_fields: None or list of str's
        @return: content unit from the content type collection that matches the
                 keys dict
        @rtype: dict
        @raise: ValueError if the unit_keys_dict is invalid
        @raise: L{MissingResource} if no content unit in the content type
                collection matches the keys dict
        """
        units = self.get_multiple_units_by_keys_dicts(content_type,
                                                      (unit_keys_dict,),
                                                      model_fields)
        if not units:
            raise MissingResource(_('No content unit for keys: %(k)s') %
                                      {'k': pformat(unit_keys_dict)})
        return units[0]

    def get_content_unit_by_id(self, content_type, unit_id, model_fields=None):
        """
        Look up an individual content unit in the corresponding content type
        collection using the given id.
        @param content_type: unique id of content collection
        @type content_type: str
        @param unit_id: unique id of content unit
        @type unit_id: str
        @param model_fields: fields of each content unit to report,
                             None means all fields
        @type model_fields: None or list of str's
        @return: content unit from the content type collection that matches the
                 given id
        @rtype: dict
        @raise: L{MissingResource} if no content unit in the content type
                collection matches the id
        """
        units = self.get_multiple_units_by_ids(content_type,
                                               (unit_id,),
                                               model_fields)
        if not units:
            raise MissingResource(_('No content unit found for: %(i)s') %
                                      {'i': unit_id})
        return units[0]

    def get_multiple_units_by_keys_dicts(self, content_type, unit_keys_dicts, model_fields=None):
        """
        Look up multiple content units in the collection for the given content
        type collection that match the list of keys dictionaries.
        @param content_type: unique id of content collection
        @type content_type: str
        @param unit_keys_dicts: list of dictionaries whose key, value pairs can
                                uniquely identify a content unit
        @type unit_keys_dicts: list of dict's
        @param model_fields: fields of each content unit to report,
                             None means all fields
        @type model_fields: None or list of str's
        @return: tuple of content units found in the content type collection
                 that match the given unit keys dictionaries
        @rtype: (possibly empty) tuple of dict's
        @raise ValueError if any of the keys dictionaries are invalid
        """
        collection = content_types_db.type_units_collection(content_type)
        spec = _build_multi_keys_spec(content_type, unit_keys_dicts)
        cursor = collection.find(spec, fields=model_fields)
        return tuple(cursor)

    def get_multiple_units_by_ids(self, content_type, unit_ids, model_fields=None):
        """
        Look up multiple content units in the collection for the given content
        type collection that match the list of ids.
        @param content_type: unique id of content collection
        @type content_type: str
        @param unit_ids: list of unique content unit ids
        @type unit_ids: list of str's
        @param model_fields: fields of each content unit to report,
                             None means all fields
        @type model_fields: None or list of str's
        @return: tuple of content units found in the content type collection
                 that match the given ids
        @rtype: (possibly empty) tuple of dict's
        """
        collection = content_types_db.type_units_collection(content_type)
        cursor = collection.find({'_id': {'$in': unit_ids}}, fields=model_fields)
        return tuple(cursor)

    def get_content_unit_keys(self, content_type, unit_ids):
        """
        Return the keys and values that will uniquely identify the content units
        that match the given unique ids.
        @param content_type: unique id of content collection
        @type content_type: str
        @param unit_ids: list of unique content unit ids
        @type unit_ids: list of str's
        @return: two tuples of the same length, one of ids the second of key dicts
                 the same index in each tuple corresponds to a single content unit
        @rtype: tuple of (possibly empty) tuples
        """
        key_fields = content_types_db.type_units_unit_key(content_type)
        if key_fields is None:
            raise InvalidValue(['content_type'])
        all_fields = ['_id']
        _flatten_keys(all_fields, key_fields)
        collection = content_types_db.type_units_collection(content_type)
        cursor = collection.find({'_id': {'$in': unit_ids}}, fields=all_fields)
        dicts = tuple(dict(d) for d in cursor)
        ids = tuple(d.pop('_id') for d in dicts)
        return (ids, dicts)

    def get_content_unit_ids(self, content_type, units_keys):
        """
        Return the ids that uniquely identify the content units that match the
        given unique keys dictionaries.
        @param content_type: unique id of content collection
        @type content_type: str
        @param unit_keys: list of keys dictionaries that uniquely identify
                          content units in the given content type collection
        @type unit_keys: list of dict's
        @return: two tuples of the same length, one of ids the second of key dicts
                 the same index in each tuple corresponds to a single content unit
        @rtype: tuple of (possibly empty) tuples
        """
        assert units_keys
        collection = content_types_db.type_units_collection(content_type)
        spec = _build_multi_keys_spec(content_type, units_keys)
        fields = ['_id']
        fields.extend(units_keys[0].keys()) # requires assertion
        cursor = collection.find(spec, fields=fields)
        dicts = tuple(dict(d) for d in cursor)
        ids = tuple(d.pop('_id') for d in dicts)
        return (ids, dicts)

    def get_root_content_dir(self, content_type):
        """
        Get the full path to Pulp's root conent directory for a given content
        type.
        @param content_type: unique id of content collection
        @type content_type: str
        @return: file system path for content type's root directory
        @rtype: str
        """
        # I'm partitioning the content on the file system based on content type
        root = os.path.join(LOCAL_STORAGE, 'content', content_type)
        if not os.path.exists(root):
            os.makedirs(root)
        return root

    def request_content_unit_file_path(self, content_type, relative_path):
        """
        @param content_type: unique id of content collection
        @type content_type: str
        @param relative_path: on disk path of a content unit relative to the
                              root directory for the given content type
        @type relative_path: str
        @return: full file system path for given relative path
        @rtype: str
        """

        # Strip off the leading / if it exists; the importer may be sloppy and
        # hand it in and its presence breaks makedirs
        if relative_path.startswith('/'):
            relative_path = relative_path[1:]

        unit_path = os.path.join(self.get_root_content_dir(content_type), relative_path)
        unit_dir = os.path.dirname(unit_path)
        if not os.path.exists(unit_dir):
            os.makedirs(unit_dir)
        return unit_path

# utility methods --------------------------------------------------------------

def _flatten_keys(flat_keys, nested_keys):
    """
    Take list of string keys and (possibly) nested sub-lists and flatten it out
    into an un-nested list of string keys.
    @param flat_keys: the flat list to store all of the keys in
    @type flat_keys: list
    @param nested_keys: possibly nested list of string keys
    @type nested_keys: list
    """
    if not nested_keys:
        return
    for key in nested_keys:
        if isinstance(key, basestring):
            flat_keys.append(key)
        else:
            _flatten_keys(flat_keys, key)


def _build_multi_keys_spec(content_type, unit_keys_dicts):
    """
    Build a mongo db spec document for a query on the given content_type
    collection out of multiple content unit key dictionaries.
    @param content_type: unique id of the content type collection
    @type content_type: str
    @param unit_key_dict: list of key dictionaries whose key, value pairs can be
                          used as unique identifiers for a single content unit
    @return: mongo db spec document for locating documents in a collection
    @rtype: dict
    @raise: ValueError if any of the key dictionaries do not match the unique
            fields of the collection
    """
    # NOTE this is just about the coolest mongo db query construction method
    # you'll find in this entire code base. Not only is it correct in the sense
    # that it builds a spec doc that will find at most 1 content unit per keys
    # dictionary passed in, but it does duplicate value elimination and key
    # validation on every single key and value found in every keys dictionary.
    # The spec document returned allows us to find multiple documents in a
    # content type collection with only a single query to the database.

    # I will buy a meal (including drinks if wanted) for the first person that
    # explains to me why the returned spec document is correct. Here's a hint:
    # explain why the spec document finds at most one document per keys dict and
    # explain when the spec will fail to find a document for an arbitrary keys
    # dict.

    # keys dicts validation constants
    key_fields = []
    _flatten_keys(key_fields, content_types_db.type_units_unit_key(content_type))
    key_fields_set = set(key_fields)
    extra_keys_msg = _('keys dictionary found with superfluous keys %(a)s, valid keys are %(b)s')
    missing_keys_msg = _('keys dictionary missing keys %(a)s, required keys are %(b)s')
    keys_errors = []
    # spec document valid keys and valid values, used as template to generate
    # actual spec document for mongo db queries
    spec_template = dict([(f, set()) for f in key_fields])
    for keys_dict in unit_keys_dicts:
        # keys dict validation
        keys_dict_set = set(keys_dict)
        extra_keys = keys_dict_set.difference(key_fields_set)
        if extra_keys:
            keys_errors.append(extra_keys_msg % {'a': ','.join(extra_keys), 'b': ','.join(key_fields)})
        missing_keys = key_fields_set.difference(keys_dict_set)
        if missing_keys:
            keys_errors.append(missing_keys_msg % {'a': ','.join(missing_keys), 'b': ','.join(key_fields)})
        if extra_keys or missing_keys:
            continue
        # validation passed, store the keys and values in the template
        for k, v in keys_dict.items():
            spec_template[k].add(v)
    if keys_errors:
        value_error_msg = '\n'.join(keys_errors)
        raise ValueError(value_error_msg)
    spec = dict([(k, {'$in': list(v)}) for k, v in spec_template.items()])
    return spec
