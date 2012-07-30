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

import mock
from pulp.plugins.conduits.profiler import ProfilerConduit

def get_repo(repo_id):
    class Repo(object):
        def __init__(self, repo_id):
            self.id = repo_id
    return Repo(repo_id)

def get_profiler_conduit(type_id=None, existing_units=None, repo_bindings=[]):
    def get_bindings(consumer_id=None):
        return repo_bindings

    def get_units(repo_id, criteria=None):
        ret_val = []
        if existing_units:
            for u in existing_units:
                if criteria:
                    if u.type_id in criteria.type_ids:
                        ret_val.append(u)
                else:
                    ret_val.append(u)
        return ret_val
    sync_conduit = mock.Mock(spec=ProfilerConduit)
    sync_conduit.get_units.side_effect = get_units
    sync_conduit.get_bindings.side_effect = get_bindings
    return sync_conduit

