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
Contains profiler management classes
"""

import pulp.plugins.loader as plugin_loader
from logging import getLogger


_LOG = getLogger(__name__)


class ProfilerManager(object):
    """
    Manages consumer profilers.
    """

    def get_profiler(self, type_id):
        """
        Find a profiler by content type ID.
        @param type_id: A content type ID.
        @type type_id: str
        @return: The requested profiler.
        @rtype: L{Profiler}
        @raise MissingResource: When not found.
        """
        pass