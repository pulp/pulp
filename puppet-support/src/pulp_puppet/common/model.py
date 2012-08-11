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


class RepositoryMetadata(object):

    @classmethod
    def from_json(cls, metadata_json):
        """
        Parses the repository metadata JSON document into an object
        representation.

        :return: object representing the repository and all of its modules
        :rtype:  RepositoryMetadata
        """

        parsed = json.loads(metadata_json)

        repo_metadata = cls()

        # The contents of the metadata document is a list of dictionaries,
        # each represnting a single module.
        for module_dict in parsed:
            module = Module.from_dict(module_dict)
            repo_metadata.modules.append(module)

        return repo_metadata

    def __init__(self):
        self.modules = []

    def to_json(self):
        """
        Serializes the repository metadata into its JSON representation.
        """
        module_dicts = [m.to_json(m) for m in self.modules]
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

        # Example Metadata Snippet:
        # {"tag_list": ["postfix","applications"],
        #  "project_url":"http://www.example42.com",
        #  "name":"postfix",
        #  "author":"lab42",
        #  "releases":[{"version":"0.0.1"},{"version":"0.0.2"}]
        #  "desc":"Test Postfix module.",
        #  "version":"0.0.2",
        #  "full_name":"lab42/postfix"}

        # The unique identifier fields are all required and should be present
        name    = module_dict.get('name')
        version = module_dict.get('version')
        author  = module_dict.get('author')

        module = Module(name, version, author)

        # I'm not sure how many of the remaining fields are optional, so
        # assume any can be missing and use None as the value in that case
        module.full_name = module_dict.get('full_name', None)
        module.description = module_dict.get('desc', None)
        module.tag_list = module_dict.get('tag_list', None)
        module.project_url = module_dict.get('project_url', None)
        module.releases = module_dict.get('releases', None)

        return module

    def __init__(self, name, version, author):

        # Unit Key Fields
        self.name = name
        self.version = version
        self.author = author

        # Extra Metadata Fields
        self.full_name = None
        self.description = None
        self.tag_list = None
        self.project_url = None
        self.releases = None

    def to_dict(self):
        """
        Returns a dict view on the module in the same format as was parsed from
        from_dict.

        :return: dict view on the module
        :rtype:  dict
        """

        # Example Metadata Snippet:
        # {"tag_list": ["postfix","applications"],
        #  "project_url":"http://www.example42.com",
        #  "name":"postfix",
        #  "author":"lab42",
        #  "releases":[{"version":"0.0.1"},{"version":"0.0.2"}]
        #  "desc":"Test Postfix module.",
        #  "version":"0.0.2",
        #  "full_name":"lab42/postfix"}

        d = {
            'tag_list'    : self.tag_list,
            'project_url' : self.project_url,
            'name'        : self.name,
            'author'      : self.author,
            'releases '   : self.releases,
            'desc'        : self.description,
            'version'     : self.version,
            'full_name'   : self.full_name,
        }
        return d

    def unit_key(self):
        """
        Returns the unit key for this module that will uniquely identify
        it in Pulp.
        """
        return {
            'name'    : self.name,
            'version' : self.version,
            'author'  : self.author,
        }

    def unit_metadata(self):
        """
        Returns all non-unit key metadata that should be stored in Pulp
        for this module.
        """
        return {
            'full_name'   : self.full_name,
            'description' : self.description,
            'tag_list'    : self.tag_list,
            'project_url' : self.project_url,
            'releases'    : self.releases,
        }