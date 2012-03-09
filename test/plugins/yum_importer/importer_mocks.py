# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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
import mock
from pulp.server.content.conduits.repo_sync import RepoSyncConduit
from pulp.server.content.plugins.config import PluginCallConfiguration
from pulp.server.content.plugins.model import Unit


def get_sync_conduit(type_id=None, existing_units=None, pkg_dir=None):
    def side_effect(type_id, key, metadata, rel_path):
        if rel_path and pkg_dir:
            rel_path = os.path.join(pkg_dir, rel_path)
        unit = Unit(type_id, key, metadata, rel_path)
        return unit

    def get_units(criteria=None):
        ret_units = True
        if criteria and hasattr(criteria, "type_ids"):
            if type_id and type_id not in criteria.type_ids:
                ret_units = False
        if ret_units and existing_units:
            return existing_units
        return []

    sync_conduit = mock.Mock(spec=RepoSyncConduit)
    sync_conduit.init_unit.side_effect = side_effect
    sync_conduit.get_units = mock.Mock()
    sync_conduit.get_units.side_effect = get_units
    return sync_conduit

def get_basic_config(feed_url, num_threads=1,
        remove_old=False, num_old_packages=0, newest=False):
    def side_effect(arg):
        result = {
            "feed_url":feed_url,
            "num_threads":num_threads,
            "remove_old":remove_old,
            "num_old_packages":num_old_packages,
            "newest":newest
           }
        if result.has_key(arg):
            return result[arg]
        return None
    config = mock.Mock(spec=PluginCallConfiguration)
    config.get.side_effect = side_effect
    return config
