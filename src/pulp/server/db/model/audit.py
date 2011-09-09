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

import datetime

from pulp.common import dateutils
from pulp.server.db.model.base import Model


class Event(Model):
    """
    Auditing models used to log and persist events in the database
    """

    collection_name = 'events'
    search_indices = ('timestamp', 'principal', 'api')

    def __init__(self, principal, action, api=None, method=None, params=[]):
        super(Event, self).__init__()
        timestamp = datetime.datetime.now(dateutils.utc_tz())
        self.timestamp = unicode(dateutils.format_iso8601_datetime(timestamp))
        self.principal_type = unicode(str(type(principal)))
        self.principal = unicode(principal)
        self.action = action
        self.api = api
        self.method = method
        self.params = params
        self.result = None
        self.exception = None
        self.traceback = None
