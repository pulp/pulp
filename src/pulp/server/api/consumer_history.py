#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
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

'''
Publicly accessible consumer history related API methods.
'''

# Python
import logging

# Pulp
from pulp.server.api.base import BaseApi
from pulp.server.api.consumer import ConsumerApi
from pulp.server.db.connection import get_object_db
from pulp.server.db.model import ConsumerHistoryEvent
from pulp.server.pexceptions import PulpException
from pulp.server.tasking.task import Task

# -- constants ----------------------------------------

LOG = logging.getLogger(__name__)

TYPE_CONSUMER_CREATED = 'consumer_created'
TYPE_CONSUMER_DELETED = 'consumer_deleted'
TYPE_REPO_BOUND = 'repo_bound'
TYPE_REPO_UNBOUND = 'repo_unbound'
TYPE_PACKAGE_INSTALLED = 'package_installed'
TYPE_PACKAGE_UNINSTALLED = 'package_uninstalled'
TYPE_PROFILE_CHANGED = 'profile_changed'

TYPES = (TYPE_CONSUMER_CREATED, TYPE_CONSUMER_DELETED, TYPE_REPO_BOUND,
         TYPE_REPO_UNBOUND, TYPE_PACKAGE_INSTALLED, TYPE_PACKAGE_UNINSTALLED,
         TYPE_PROFILE_CHANGED)

# Used to identify an event as triggered by the consumer (as compared to an admin)
ORIGINATOR_CONSUMER = 'consumer'


class ConsumerHistoryApi(BaseApi):

    # -- setup ----------------------------------------

    def __init__(self):
        BaseApi.__init__(self)
        self.consumer_api = ConsumerApi()

    def _getcollection(self):
        return get_object_db('consumer_history',
                             self._unique_indexes,
                             self._indexes)

    # -- public api ----------------------------------------

    def query(self, consumer_id=None, event_type=None, limit=None):

        # Verify the consumer ID represents a valid consumer
        if consumer_id and not self.consumer_api.consumer(consumer_id):
            raise PulpException('Invalid consumer ID [%s]' % consumer_id)

        # Verify the event type is valid
        if event_type and event_type not in TYPES:
            raise PulpException('Invalid event type [%s]' % event_type)

        # Assemble the mongo search parameters
        search_params = {}
        if consumer_id:
            search_params['consumer_id'] = consumer_id
        if event_type:
            search_params['type_name'] = event_type

        # Determine the correct mongo cursor to retrieve
        if len(search_params) == 0:
            cursor = self.objectdb.find()
        else:
            cursor = self.objectdb.find(search_params)

        # If a limit was specified, add it to the cursor
        if limit:
            cursor.limit(limit)

        # Finally convert to a list before returning
        return list(cursor)

    def event_types(self):
        return TYPES

    # -- internal ----------------------------------------

    def consumer_created(self, consumer_id, originator=ORIGINATOR_CONSUMER):
        event = ConsumerHistoryEvent(consumer_id, originator, TYPE_CONSUMER_CREATED, None)
        self.insert(event)

    def consumer_deleted(self, consumer_id, originator=ORIGINATOR_CONSUMER):
        event = ConsumerHistoryEvent(consumer_id, originator, TYPE_CONSUMER_DELETED, None)
        self.insert(event)

    def repo_bound(self, consumer_id, repo_id, originator=ORIGINATOR_CONSUMER):
        details = {'repo_id' : repo_id}
        event = ConsumerHistoryEvent(consumer_id, originator, TYPE_REPO_BOUND, details)
        self.insert(event)

    def repo_unbound(self, consumer_id, repo_id, originator=ORIGINATOR_CONSUMER):
        details = {'repo_id' : repo_id}
        event = ConsumerHistoryEvent(consumer_id, originator, TYPE_REPO_UNBOUND, details)
        self.insert(event)

    def packages_installed(self, consumer_id, package_nveras, originator=ORIGINATOR_CONSUMER):
        if type(package_nveras) != list:
            package_nveras = [package_nveras]

        details = {'package_nveras' : package_nveras}
        event = ConsumerHistoryEvent(consumer_id, originator, TYPE_PACKAGE_INSTALLED, details)
        self.insert(event)

    def packages_removed(self, consumer_id, package_nveras, originator=ORIGINATOR_CONSUMER):
        if type(package_nveras) != list:
            package_nveras = [package_nveras]

        details = {'package_nveras' : package_nveras}
        event = ConsumerHistoryEvent(consumer_id, originator, TYPE_PACKAGE_UNINSTALLED, details)
        self.insert(event)

    def profile_changed(self, consumer_id, profile_details):
        pass
