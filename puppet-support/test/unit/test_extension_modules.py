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

from pulp.client.commands import options
from pulp.client.commands.criteria import UnitAssociationCriteriaCommand

import base_cli
from pulp.client.extensions.core import TAG_DOCUMENT
from pulp_puppet.extension.admin import modules

# -- constants ----------------------------------------------------------------

SAMPLE_RESPONSE_BODY =[
    {
    "updated": "2012-08-29T14:39:39",
    "repo_id": "blog-repo",
    "created": "2012-08-29T14:39:39",
    "_ns": "repo_content_units",
    "unit_id": "1e6ef714-51fe-4233-976f-fc6374cbeb60",
    "metadata": {
        "_storage_path": "/var/lib/pulp/content/puppet_module/thias-apache_httpd-0.3.2.tar.gz",
        "license ": "Apache 2.0",
        "description": "Install and enable the Apache httpd web server and manage its configuration with snippets.",
        "author": "thias",
        "_ns": "units_puppet_module",
        "_id": "1e6ef714-51fe-4233-976f-fc6374cbeb60",
        "project_page": "http://glee.thias.es/puppet",
        "summary": "Apache HTTP Daemon installation and configuration",
        "source": "git://github.com/thias/puppet-modules/modules/apache_httpd",
        "dependencies": [],
        "version": "0.3.2",
        "_content_type_id": "puppet_module",
        "checksums": [["files/trace.inc", "00b0ef3384ae0ae23641de16a4f409c2"],],
        "tag_list": ["webservers", "apache"],
        "types": [],
        "name": "apache_httpd"
    },
    "unit_type_id": "puppet_module",
    "owner_type": "importer",
    "_id": {"$oid": "503e61eb8a905b3cc5000034"},
    "id": "503e61eb8a905b3cc5000034",
    "owner_id": "puppet_importer"
    },
        {
        "updated": "2012-08-29T14:39:39",
        "repo_id": "blog-repo",
        "created": "2012-08-29T14:39:39",
        "_ns": "repo_content_units",
        "unit_id": "1e6ef714-51fe-4233-976f-fc6374cbeb61",
        "metadata": {
            "_storage_path": "/var/lib/pulp/content/puppet_module/thias-apache_httpd-1.3.2.tar.gz",
            "license ": "Apache 2.0",
            "description": "Install and enable the Apache httpd web server and manage its configuration with snippets.",
            "author": "thias",
            "_ns": "units_puppet_module",
            "_id": "1e6ef714-51fe-4233-976f-fc6374cbeb60",
            "project_page": "http://glee.thias.es/puppet",
            "summary": "Apache HTTP Daemon installation and configuration",
            "source": "git://github.com/thias/puppet-modules/modules/apache_httpd",
            "dependencies": [],
            "version": "1.3.2",
            "_content_type_id": "puppet_module",
            "checksums": [["files/trace.inc", "00b0ef3384ae0ae23641de16a4f409c2"],],
            "tag_list": ["webservers", "apache"],
            "types": [],
            "name": "apache_httpd"
        },
        "unit_type_id": "puppet_module",
        "owner_type": "importer",
        "_id": {"$oid": "503e61eb8a905b3cc5000034"},
        "id": "503e61eb8a905b3cc5000034",
        "owner_id": "puppet_importer"
    }
]

# -- test cases ---------------------------------------------------------------

class ModulesCommandTests(base_cli.ExtensionTests):

    def setUp(self):
        super(ModulesCommandTests, self).setUp()
        self.command = modules.ModulesCommand(self.context)

    def test_structure(self):
        self.assertTrue(isinstance(self.command, UnitAssociationCriteriaCommand))
        self.assertEqual('modules', self.command.name)
        self.assertEqual(modules.DESC_SEARCH, self.command.description)

    def test_modules(self):
        # Setup
        data = {
            options.OPTION_REPO_ID.keyword : 'test-repo',
        }

        self.server_mock.request.return_value = 200, SAMPLE_RESPONSE_BODY

        # Test
        self.command.run(**data)

        # Verify - make sure the first three lines are the correct order and do
        # not have the association information
        self.assertTrue(self.recorder.lines[0].startswith('Name'))
        self.assertTrue(self.recorder.lines[1].startswith('Version'))
        self.assertTrue(self.recorder.lines[2].startswith('Author'))

    def test_modules_with_metadata(self):
        # Setup
        data = {options.OPTION_REPO_ID.keyword : 'test-repo',
                UnitAssociationCriteriaCommand.ASSOCIATION_FLAG.keyword: True}

        self.server_mock.request.return_value = 200, SAMPLE_RESPONSE_BODY

        # Test
        self.command.run(**data)

        # Verify - make sure the first line is from the association data
        self.assertTrue(self.recorder.lines[0].startswith('Created'))
