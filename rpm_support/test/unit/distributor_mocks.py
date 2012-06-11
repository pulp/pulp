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
import os
import mock
from pulp.server.content.conduits.repo_publish import RepoPublishConduit
from pulp.server.content.plugins.config import PluginCallConfiguration
from pulp.server.content.plugins.model import PublishReport, Unit

def get_publish_conduit(type_id=None, existing_units=None, pkg_dir=None, checksum_type="sha"):
    def build_success_report(summary, details):
        return PublishReport(True, summary, details)

    def build_failure_report(summary, details):
        return PublishReport(False, summary, details)

    def get_units(criteria=None):
        ret_units = True
        if criteria and hasattr(criteria, "type_ids"):
            if type_id and type_id not in criteria.type_ids:
                ret_units = False
        if ret_units and existing_units:
            return existing_units
        return []

    def get_repo_scratchpad():
        scratchpad = None
        if checksum_type:
            scratchpad = {"checksum_type" : checksum_type}
        return scratchpad

    publish_conduit = mock.Mock(spec=RepoPublishConduit)
    publish_conduit.get_units = mock.Mock()
    publish_conduit.get_units.side_effect = get_units
    publish_conduit.build_failure_report = mock.Mock()
    publish_conduit.build_failure_report = build_failure_report
    publish_conduit.build_success_report = mock.Mock()
    publish_conduit.build_success_report = build_success_report
    publish_conduit.get_repo_scratchpad = mock.Mock()
    publish_conduit.get_repo_scratchpad.side_effect = get_repo_scratchpad
    return publish_conduit



def get_basic_config(*arg, **kwargs):
    plugin_config = {}
    repo_plugin_config = {}
    for key in kwargs:
        repo_plugin_config[key] = kwargs[key]
    config = PluginCallConfiguration(plugin_config, 
            repo_plugin_config=repo_plugin_config)
    return config
