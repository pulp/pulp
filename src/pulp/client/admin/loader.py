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


from pulp.client.pluginlib.loader import PluginLoader
from pulp.client.admin.plugin import AdminPlugin


class AdminPluginLoader(PluginLoader):

    plugin_base_class = AdminPlugin
    plugin_dirs = ["/usr/lib/pulp-admin-plugins"]
