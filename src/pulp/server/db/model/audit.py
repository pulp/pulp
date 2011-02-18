# -*- coding: utf-8 -*-

# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import datetime

from pulp.server.db.model.base import Base


class Event(Base):
    """
    Auditing models used to log and persist events in the database
    """

    other_indicies = ('timestamp', 'principal', 'api')

    def __init__(self, principal, action, api=None, method=None, params=[]):
        super(Event, self).__init__()
        self.timestamp = datetime.datetime.now()
        self.principal_type = unicode(str(type(principal)))
        self.principal = unicode(principal)
        self.action = action
        self.api = api
        self.method = method
        self.params = params
        self.result = None
        self.exception = None
        self.traceback = None
