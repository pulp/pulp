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

from pulp.server.db.model.base import Model


class CDS(Model):
    '''
    Represents an external CDS instance managed by this pulp server.
    '''

    unique_indicies = ('hostname',)

    def __init__(self, hostname, name=None, description=None):
        Model.__init__(self)
        self.hostname = hostname
        if name:
            self.name = name
        else:
            self.name = hostname
        self.description = description
        self.repo_ids = []
        self.last_sync = None

    def __str__(self):
        return self.hostname


class CDSHistoryEvent(Model):
    '''
    Represents a single event that occurred on a CDS.
    '''

    def __init__(self, cds_hostname, originator, type_name, details=None):
        Model.__init__(self)
        self.cds_hostname = cds_hostname
        self.originator = originator
        self.type_name = type_name
        self.details = details
        self.timestamp = datetime.datetime.now()


class CDSHistoryEventType(object):
    '''
    Enumeration of possible history event types. This corresponds to the type_name attribute
    on the CDSHistoryEvent class.
    '''
    REGISTERED = 'registered'
    UNREGISTERED = 'unregistered'
    SYNC_STARTED = 'sync_started'
    SYNC_FINISHED = 'sync_finished'
    REPO_ASSOCIATED = 'repo_associated'
    REPO_UNASSOCIATED = 'repo_unassociated'

    TYPES = (REGISTERED, UNREGISTERED, SYNC_STARTED, SYNC_FINISHED, REPO_ASSOCIATED, REPO_UNASSOCIATED)
