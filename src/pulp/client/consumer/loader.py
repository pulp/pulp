# -*- coding: utf-8 -*-

# Copyright © 2010 Red Hat, Inc.
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

from pulp.client.pluginlib.loader import PluginLoader
from pulp.client.consumer import plugins
from pulp.client.consumer.plugin import ConsumerPlugin


class ConsumerPluginLoader(PluginLoader):
    """
    Pulp admin plugin loader.
    """

    plugin_base_class = ConsumerPlugin

    def get_plugin_dirs(self):
        """
        Append the default install locations for admin plugins to the list of
        plugin directories.
        """
        plugin_dirs = PluginLoader.get_plugin_dirs(self)
        return plugin_dirs + [os.path.dirname(plugins.__file__)]
