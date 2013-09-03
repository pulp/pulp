# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import mock

import base
from pulp.plugins.loader import api


class TestAPI(base.PulpServerTests):
    @mock.patch('pulp.plugins.loader.loading.load_plugins_from_entry_point', autospec=True)
    def test_init_calls_entry_points(self, mock_load):
        api._MANAGER = None
        # This test is problematic, because it relies on the pulp_rpm package, which depends on this
        # package. We should really mock the type loading and test that the mocked types were loaded
        # For now, we can get around the problem by just calling load_content_types.
        api.load_content_types()
        api.initialize()
        # calls for 5 types of plugins
        self.assertEqual(mock_load.call_count, 5)
