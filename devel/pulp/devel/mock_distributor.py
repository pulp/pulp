# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
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
from pulp.plugins.conduits.repo_publish import RepoPublishConduit
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.model import PublishReport

def get_publish_conduit(type_id=None, existing_units=None, pkg_dir=None, checksum_type="sha", repodata=None):
    def build_success_report(summary, details):
        return PublishReport(True, summary, details)

    def build_failure_report(summary, details):
        return PublishReport(False, summary, details)

    def get_units(criteria=None):
        ret_val = []
        if existing_units:
            count = 0
            for u in existing_units:
                count += 1
                if criteria:
                    if count > criteria.skip:
                        if not criteria.unit_filters:
                            if u.type_id in criteria.type_ids:
                                ret_val.append(u)
                        else:
                            if u.type_id == 'erratum':
                                start_date = criteria.unit_filters['issued']['$gte']
                                end_date   = criteria.unit_filters['issued']['$lte']
                                if start_date <= u.metadata['issued'] <= end_date:
                                    ret_val.append(u)
                else:
                    ret_val.append(u)
        return ret_val

    def get_repo_scratchpad(repoid=None):
        scratchpad = None
        if checksum_type:
            scratchpad = {"checksum_type" : checksum_type}

        return scratchpad

    def get_scratchpad():
        scratchpad = None
        if checksum_type:
            scratchpad = {"checksum_type" : checksum_type, 'published_distributions' : {}}
        return scratchpad

    publish_conduit = mock.Mock(spec=RepoPublishConduit)
    publish_conduit.get_units.side_effect = get_units
    publish_conduit.build_failure_report = build_failure_report
    publish_conduit.build_success_report = build_success_report
    publish_conduit.get_repo_scratchpad.side_effect = get_repo_scratchpad
    publish_conduit.get_scratchpad.side_effect = get_scratchpad
    return publish_conduit


def get_basic_config(*arg, **kwargs):
    plugin_config = {}
    repo_plugin_config = {}
    for key in kwargs:
        repo_plugin_config[key] = kwargs[key]
    config = PluginCallConfiguration(plugin_config,
            repo_plugin_config=repo_plugin_config)
    return config
