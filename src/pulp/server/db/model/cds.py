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


class CDS(Model):
    '''
    Represents an external CDS instance managed by this pulp server.
    '''

    collection_name = 'cds'
    unique_indices = ('hostname',)

    def __init__(self, hostname, name=None, description=None):
        Model.__init__(self)
        self._id = hostname
        self.id = hostname
        self.hostname = hostname
        if name:
            self.name = name
        else:
            self.name = hostname
        self.description = description
        self.repo_ids = []
        self.last_sync = None
        self.secret = None
        self.sync_schedule = None
        self.cluster_id = None # not a list, only a single cluster at a time

    def __str__(self):
        return self.hostname


class CDSHistoryEvent(Model):
    '''
    Represents a single event that occurred on a CDS.
    '''

    collection_name = 'cds_history'

    def __init__(self, cds_hostname, originator, type_name, details=None):
        Model.__init__(self)
        self.cds_hostname = cds_hostname
        self.originator = originator
        self.type_name = type_name
        self.details = details
        now = datetime.datetime.now(dateutils.utc_tz())
        self.timestamp = dateutils.format_iso8601_datetime(now)


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


class CDSRepoRoundRobin(Model):
    '''
    Holds the necessary data for the round robin algorithm to function. Each instance is
    scoped to a particular repo and contains information on how the CDS URL list has been
    generated in the past.
    '''
    collection_name = 'cds_repo_round_robin'
    unique_indices = ('id',)

    def __init__(self, repo_id, next_permutation):
        Model.__init__(self)
        self.id = repo_id
        self.repo_id = repo_id
        self.next_permutation = next_permutation # list of strings

    def __str__(self):
        return 'Repo [%s], next permutation [%s]' % (self.repo_id, ','.join(self.next_permutation))

class CDSSyncSchedule(Model):
    """
    Class representing a serialized CDS sync schedule.
    """
    def __init__(self, interval, start_time=None, runs=None):
        Model.__init__(self)
        self.interval = interval
        self.start_time = start_time
        self.runs = runs
