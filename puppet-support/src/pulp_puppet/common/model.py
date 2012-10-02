# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
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
Contains data structures representing puppet repository and module concepts
and methods to serialize and deserialize them.
"""

import copy

from pulp.common.compat import json

from pulp_puppet.common import constants


class RepositoryMetadata(object):

    def __init__(self):
        self.modules = []

    def update_from_json(self, metadata_json):
        """
        Updates this metadata instance with modules found in the given JSON
        document. This can be called multiple times to merge multiple
        repository metadata JSON documents into this instance.

        :return: object representing the repository and all of its modules
        :rtype:  RepositoryMetadata
        """

        parsed = json.loads(metadata_json)

        # The contents of the metadata document is a list of dictionaries,
        # each represnting a single module.
        for module_dict in parsed:
            module = Module.from_dict(module_dict)
            self.modules.append(module)

    def to_json(self):
        """
        Serializes the repository metadata into its JSON representation.
        """

        # Assemble all of the modules in dictionary form
        module_dicts = [m.to_dict() for m in self.modules]

        # For each module, we only want a small subset of data that goes in the
        # repo metadata document
        limited_module_dicts = []
        included_fields = ('name', 'author', 'version', 'tag_list')
        for m in module_dicts:
            clean_module = dict([(k, v) for k, v in m.items() if k in included_fields])
            limited_module_dicts.append(clean_module)

        # Serialize the dictionaries into a single JSON document
        serialized = json.dumps(limited_module_dicts)

        return serialized


class Module(object):

    @classmethod
    def from_dict(cls, module_dict):
        """
        Parses the given snippet of module metadata into an object
        representation. This call assumes the JSON has already been parsed
        and the dict representation is provided.

        :return: object representation of the given module
        :rtype:  Module
        """

        # The unique identifier fields are all required and should be present
        name    = module_dict.get('name')
        version = module_dict.get('version')
        author  = module_dict.get('author')

        module = Module(name, version, author)
        module.update_from_dict(module_dict)

        return module

    @classmethod
    def from_unit(cls, pulp_unit):
        """
        Converts a Pulp unit into a Module representation.

        :param pulp_unit: unit returned from the Pulp conduit
        :type  pulp_unit: pulp.plugins.model.Unit

        :return: object representation of the given module
        :rtype:  Module
        """
        unit_as_dict = copy.copy(pulp_unit.unit_key)
        unit_as_dict.update(pulp_unit.metadata)

        return cls.from_dict(unit_as_dict)

    @staticmethod
    def generate_unit_key(name, version, author):
        """
        Formats the module unique pieces into the Pulp unit key.
        :rtype: dict
        """
        return {
            'name'    : name,
            'version' : version,
            'author'  : author,
        }

    def __init__(self, name, version, author):

        # Unit Key Fields
        self.name = name
        self.version = version
        self.author = author

        # From Repository Metadata
        self.tag_list = None

        # From Module Metadata
        self.source = None
        self.license = None
        self.summary = None
        self.description = None
        self.project_page = None
        self.types = None # list of something I don't know yet :)
        self.dependencies = None # list of dicts of name to version_requirement
        self.checksums = None # dict of file name (with relative path) to checksum

    def to_dict(self):
        """
        Returns a dict view on the module in the same format as was parsed from
        update_from_dict.

        :return: dict view on the module
        :rtype:  dict
        """
        d = self.unit_key()
        d.update(self.unit_metadata())
        return d

    def update_from_json(self, metadata_json):
        """
        Takes the module's metadata in JSON format and merges it into this
        instance.

        :param metadata_json: module metadata in JSON
        :type  metadata_json: str
        """
        parsed = json.loads(metadata_json)
        self.update_from_dict(parsed)

    def update_from_dict(self, module_dict):
        """
        Updates the instance variables with the values in the given dict.
        """

        # Not all calls into this will contain the tag list
        if 'tag_list' in module_dict:
            self.tag_list = module_dict['tag_list']

        # Found in the module metadata itself
        self.source = module_dict.get('source', None)
        self.license = module_dict.get('license', None)
        self.summary = module_dict.get('summary', None)
        self.description = module_dict.get('description', None)
        self.project_page = module_dict.get('project_page', None)
        self.types = module_dict.get('types', [])
        self.dependencies = module_dict.get('dependencies', [])
        self.checksums = module_dict.get('checksums', {})

        # Special handling of the DB-safe checksum to rebuild it
        if isinstance(self.checksums, list):
            self.checksums = dict([ (c[0], c[1]) for c in self.checksums])

    def unit_key(self):
        """
        Returns the unit key for this module that will uniquely identify
        it in Pulp. This is the unique key for the inventoried module in Pulp.
        """
        return self.generate_unit_key(self.name, self.version, self.author)

    def unit_metadata(self):
        """
        Returns all non-unit key metadata that should be stored in Pulp
        for this module. This is how the module will be inventoried in Pulp.
        """
        metadata = {
            'description'  : self.description,
            'tag_list'     : self.tag_list,
            'source'       : self.source,
            'license'     : self.license,
            'summary'      : self.summary,
            'project_page' : self.project_page,
            'types'        : self.types,
            'dependencies' : self.dependencies,
        }

        # Checksums is expressed as a dict of file to checksum. This causes
        # a problem in mongo since keys can't have periods in them, but file
        # names clearly will. Translate to a list of tuples to get around this

        clean_checksums =  [ (k, v) for k, v in self.checksums.items()]
        metadata['checksums'] = clean_checksums

        return metadata

    def filename(self):
        """
        Generates the filename for the given module.

        :return: puppet standard filename for this module
        :rtype:  str
        """
        f = constants.MODULE_FILENAME % (self.author, self.name, self.version)
        return f