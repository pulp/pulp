# -*- coding: utf-8 -*-

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

import time

from pulp.server.db.model.base import Model


class Status(Model):
    """
    Status model used to record the number of times the status service has
    been called and the time of the last call.
    """

    collection_name = 'status'
    search_indices = ('timestamp')

    def __init__(self):
        super(Status, self).__init__()
        self.count = 0
        self.timestamp = time.time()
