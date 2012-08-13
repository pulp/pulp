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

try:
    import json as _json
except ImportError:
    import simplejson as _json
json = _json

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
        module_dicts = [m.to_dict() for m in self.modules]
        serialized = json.dumps(module_dicts)

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
        self.tags = None

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

        # Found in the repository metadata for the module
        self.tags = module_dict.get('tag_list', None)

        # Found in the module metadata itself
        self.source = module_dict.get('source', None)
        self.license = module_dict.get('license', None)
        self.summary = module_dict.get('summary', None)
        self.description = module_dict.get('description', None)
        self.project_page = module_dict.get('project_page', None)
        self.types = module_dict.get('types', [])
        self.dependencies = module_dict.get('dependencies', [])
        self.checksums = module_dict.get('checksums', {})

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
        return {
            'description'  : self.description,
            'tag_list'     : self.tags,
            'source'       : self.source,
            'license '     : self.license,
            'summary'      : self.summary,
            'project_page' : self.project_page,
            'types'        : self.types,
            'dependencies' : self.dependencies,
            'checksums'    : self.checksums,
        }

    def filename(self):
        """
        Generates the filename for the given module.

        :return: puppet standard filename for this module
        :rtype:  str
        """
        f = constants.MODULE_FILENAME % (self.author, self.name, self.version)
        return f