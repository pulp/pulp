#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import pulp.server.agent

class MockRepoProxy(object):
    '''
    Mock proxy to make calls against a consumer's repo service.
    '''

    def __init__(self):
        self.bind_data = None
        self.unbind_repo_id = None
        self.update_calls = []

    def bind(self, bind_data):
        self.bind_data = bind_data

    def unbind(self, repo_id):
        self.unbind_repo_id = repo_id

    def update(self, repo_id, bind_data):
        self.update_calls.append((repo_id, bind_data))

    def clear(self):
        '''
        Removes all state from the mock. Meant to be run between test runs to ensure a
        common starting point.
        '''
        self.bind_data = None
        self.unbind_repo_id = None
        self.update_calls = []

def init_repo_proxy():
    '''
    Configures the agent repo proxy retrieval to return a mock. The mock instance that will
    be used is returned from this call.

    @return: mock repo proxy instance that will be used
    @rtype:  L{MockRepoProxy}
    '''

    mock = MockRepoProxy()
    def retrieve_mock_repo_proxy(uuid, **options):
        return mock

    pulp.server.agent.retrieve_repo_proxy = retrieve_mock_repo_proxy

    return mock
