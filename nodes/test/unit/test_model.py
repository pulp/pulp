# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import httplib

from mock import patch, Mock

from pulp.common.plugins import importer_constants
from pulp.common.bundle import Bundle

from base import WebTest, Response, Task, TaskResult
from pulp_node.handlers.model import Repository
from pulp_node import constants


PULP_ID = 'pulp_1'
REPO_ID = 'repo_1'
MAX_BANDWIDTH = 12345
MAX_CONCURRENCY = 54321

NODE_CERTIFICATE = """
    -----BEGIN RSA PRIVATE KEY-----
    PULPROCKSPULPROCKSPULPROCKS
    -----END RSA PRIVATE KEY-----
    -----BEGIN CERTIFICATE-----
    PULPROCKSPULPROCKSPULPROCKS
    -----END CERTIFICATE-----
"""

PARENT_SETTINGS = {constants.NODE_CERTIFICATE: NODE_CERTIFICATE}


class TestModel(WebTest):

    def setUp(self):
        super(self.__class__, self).setUp()

    def tearDown(self):
        super(self.__class__, self).tearDown()

    @patch('pulp_node.poller.TaskPoller.join')
    @patch('pulp.bindings.repository.RepositoryActionsAPI.sync',
           return_value=Response(httplib.ACCEPTED, TaskResult(0)))
    @patch('pulp.agent.lib.conduit.Conduit.consumer_id')
    def test_repository(self, *mocks):
        # Setup
        repository = Repository(REPO_ID)
        progress = Mock()
        cancelled = Mock(return_value=False)
        # Test
        options = {
            constants.MAX_DOWNLOAD_CONCURRENCY_KEYWORD: MAX_CONCURRENCY,
            constants.MAX_DOWNLOAD_BANDWIDTH_KEYWORD: MAX_BANDWIDTH,
            constants.PARENT_SETTINGS: PARENT_SETTINGS,
        }
        repository.run_synchronization(progress, cancelled, options)
        binding = mocks[1]
        key, certificate = Bundle.split(NODE_CERTIFICATE)
        expected_conf = {
            importer_constants.KEY_SSL_VALIDATION: False,
            importer_constants.KEY_MAX_DOWNLOADS: MAX_CONCURRENCY,
            importer_constants.KEY_MAX_SPEED: MAX_BANDWIDTH,
            importer_constants.KEY_SSL_CLIENT_KEY: key,
            importer_constants.KEY_SSL_CLIENT_CERT: certificate,
        }
        # Verify
        binding.assert_called_with(REPO_ID, expected_conf)