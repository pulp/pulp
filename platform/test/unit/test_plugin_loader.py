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
from pulp.plugins.loader import loading


class TestPluginLoader(base.PulpServerTests):
    @mock.patch('pulp.plugins.loader.loading.add_plugin_to_map', autospec=True)
    @mock.patch('pkg_resources.iter_entry_points', autospec=True)
    def test_load_entry_points(self, mock_iter, mock_add):
        ep = mock.MagicMock()
        cls = mock.MagicMock()
        cfg = mock.MagicMock()
        ep.load.return_value.return_value = (cls, cfg)
        mock_iter.return_value = [ep]

        GROUP_NAME = 'abc'
        plugin_map = mock.MagicMock()

        # finally, we test
        loading.load_plugins_from_entry_point(GROUP_NAME, plugin_map)

        mock_iter.assert_called_once_with(GROUP_NAME)
        mock_add.assert_called_once_with(cls, cfg, plugin_map)
