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

"""
Profiler conduits.
"""

from pulp.server.managers import factory as managers
from pulp.plugins.conduits.mixins import MultipleRepoUnitsMixin
from pulp.plugins.conduits.mixins import ProfilerConduitException

class ProfilerConduit(MultipleRepoUnitsMixin):

    def __init__(self):
        MultipleRepoUnitsMixin.__init__(self, ProfilerConduitException)

    def get_bindings(self, consumer_id):
        """
        Get a list of bound repository IDs.

        @param consumer_id: A consumer ID.
        @type consumer_id: str

        @return: A list of bound repository IDs.
        @rtype: list
        """
        manager = managers.consumer_bind_manager()
        bindings = manager.find_by_consumer(consumer_id)
        return [b['repo_id'] for b in bindings]
