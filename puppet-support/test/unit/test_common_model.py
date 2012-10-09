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

import unittest

from pulp.common.compat import json

from pulp_puppet.common.model import RepositoryMetadata, Module

# -- constants ----------------------------------------------------------------

VALID_REPO_METADATA_JSON = """[
{"tag_list":["postfix","applications"],
 "project_url":"http://www.example42.com",
 "name":"postfix",
 "author":"lab42",
 "releases":[{"version":"0.0.1"},{"version":"0.0.2"}],
 "desc":"Test Postfix module.",
 "version":"0.0.2",
 "full_name":"lab42/postfix"},
{"tag_list":[],
 "project_url":"http://www.example42.com",
 "name":"common",
 "author":"lab42",
 "releases":[{"version":"0.0.1"}],
 "desc":"Example42 common resources module.",
 "version":"0.0.1",
 "full_name":"lab42/common"}
]
"""

VALID_MODULE_METADATA_JSON = """{
  "name": "jdob-valid",
  "version": "1.0.0",
  "source": "http://example.org/jdob-valid/source",
  "author": "jdob",
  "license": "Apache License, Version 2.0",
  "summary": "Valid Module Summary",
  "description": "Valid Module Description",
  "project_page": "http://example.org/jdob-valid",
  "dependencies": [
    {
      "name": "jdob/dep-alpha",
      "version_requirement": ">= 1.0.0"
    },
    {
      "name": "ldob/dep-beta",
      "version_requirement": ">= 2.0.0"
    }
  ],
  "types": [],
  "checksums": {
    "Modulefile": "704cecf2957448dcf7fa20cffa2cf7c1",
    "README": "11edd8578497566d8054684a8c89c6cb",
    "manifests/init.pp": "1d1fb26825825b4d64d37d377016869e",
    "spec/spec_helper.rb": "a55d1e6483344f8ec6963fcb2c220372",
    "tests/init.pp": "7043c7ef0c4b0ac52b4ec6bb76008ebd"
  }
}
"""

# -- test cases ---------------------------------------------------------------

class RepositoryMetadataTests(unittest.TestCase):

    def test_update_from_json(self):
        # Test
        metadata = RepositoryMetadata()
        metadata.update_from_json(VALID_REPO_METADATA_JSON)

        # Verify
        self.assertEqual(2, len(metadata.modules))
        for m in metadata.modules:
            self.assertTrue(isinstance(m, Module))

        sorted_modules = sorted(metadata.modules, key=lambda x : x.name)

        self.assertEqual(sorted_modules[0].name, 'common')
        self.assertEqual(sorted_modules[0].author, 'lab42')
        self.assertEqual(sorted_modules[0].version, '0.0.1')
        self.assertEqual(sorted_modules[0].tag_list, [])
        self.assertEqual(sorted_modules[0].description, None)
        self.assertEqual(sorted_modules[0].project_page, None)

        self.assertEqual(sorted_modules[1].name, 'postfix')
        self.assertEqual(sorted_modules[1].author, 'lab42')
        self.assertEqual(sorted_modules[1].version, '0.0.2')
        self.assertEqual(sorted_modules[1].tag_list, ['postfix', 'applications'])
        self.assertEqual(sorted_modules[1].description, None)
        self.assertEqual(sorted_modules[1].project_page, None)

    def test_to_json(self):
        # Setup
        metadata = RepositoryMetadata()
        metadata.update_from_json(VALID_REPO_METADATA_JSON)

        # Test
        serialized = metadata.to_json()

        # Verify
        parsed = json.loads(serialized)

        self.assertEqual(2, len(parsed))

        sorted_modules = sorted(parsed, key=lambda x : x['name'])

        self.assertEqual(4, len(sorted_modules[0]))
        self.assertEqual(sorted_modules[0]['name'], 'common')
        self.assertEqual(sorted_modules[0]['author'], 'lab42')
        self.assertEqual(sorted_modules[0]['version'], '0.0.1')
        self.assertEqual(sorted_modules[0]['tag_list'], [])

        self.assertEqual(4, len(sorted_modules[1]))
        self.assertEqual(sorted_modules[1]['name'], 'postfix')
        self.assertEqual(sorted_modules[1]['author'], 'lab42')
        self.assertEqual(sorted_modules[1]['version'], '0.0.2')
        self.assertEqual(sorted_modules[1]['tag_list'], ['postfix', 'applications'])


class ModuleTests(unittest.TestCase):

    def test_from_dict(self):
        # Setup
        pass

    def test_update_from_json(self):
        # Setup
        module = Module('jdob-valid', '1.0.0', 'jdob')

        # Test
        module.update_from_json(VALID_MODULE_METADATA_JSON)

        # Verify
        self.assert_valid_module(module)

    def test_from_dict(self):
        # Setup
        data = json.loads(VALID_MODULE_METADATA_JSON)

        # Test
        module = Module.from_dict(data)

        # Verify
        self.assert_valid_module(module)

    def assert_valid_module(self, module):
        self.assertEqual(module.name, 'jdob-valid')
        self.assertEqual(module.version, '1.0.0')
        self.assertEqual(module.author, 'jdob')
        self.assertEqual(module.source, 'http://example.org/jdob-valid/source')
        self.assertEqual(module.license, 'Apache License, Version 2.0')
        self.assertEqual(module.summary, 'Valid Module Summary')
        self.assertEqual(module.description, 'Valid Module Description')
        self.assertEqual(module.project_page, 'http://example.org/jdob-valid')

        self.assertEqual(2, len(module.dependencies))
        sorted_deps = sorted(module.dependencies, key=lambda x : x['name'])
        self.assertEqual(sorted_deps[0]['name'], 'jdob/dep-alpha')
        self.assertEqual(sorted_deps[0]['version_requirement'], '>= 1.0.0')
        self.assertEqual(sorted_deps[1]['name'], 'ldob/dep-beta')
        self.assertEqual(sorted_deps[1]['version_requirement'], '>= 2.0.0')

        self.assertEqual(module.types, [])

        expected_checksums = {
            'Modulefile': '704cecf2957448dcf7fa20cffa2cf7c1',
            'README': '11edd8578497566d8054684a8c89c6cb',
            'manifests/init.pp': '1d1fb26825825b4d64d37d377016869e',
            'spec/spec_helper.rb': 'a55d1e6483344f8ec6963fcb2c220372',
            'tests/init.pp': '7043c7ef0c4b0ac52b4ec6bb76008ebd'
        }
        self.assertEqual(module.checksums, expected_checksums)
