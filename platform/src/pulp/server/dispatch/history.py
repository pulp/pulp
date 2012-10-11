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

import datetime
import threading
import time

from pulp.common import dateutils
from pulp.server import config as pulp_config
from pulp.server.db.model.dispatch import ArchivedCall

# public api -------------------------------------------------------------------

def archive_call(call_request, call_report):
    """
    Store a completed call request in the database.
    @param call_request: call request to store
    @type call_request: L{pulp.server.dispatch.call.CallRequest}
    @param call_report: call report corresponding to the call request
    @type call_report: L{pulp.server.dispatch.call.CallReport}
    """
    archived_call = ArchivedCall(call_request, call_report)
    collection = ArchivedCall.get_collection()
    collection.insert(archived_call, safe=True)


def find_archived_calls(**criteria):
    """
    Find archived call requests that match the given criteria.
    Criteria is passed in as keyword arguments.

    Currently supported criteria:
    * call_request_id
    * call_request_group_id

    @return: (possibly empty) mongo collection cursor containing the matching archived calls
    @rtype: L{pymongo.cursor.Cursor}
    """
    query = {}
    if 'call_request_id' in criteria:
        query['serialized_call_request.id'] = criteria['call_request_id']
    if 'call_request_group_id' in criteria:
        query['serialized_call_request.group_id'] = criteria['call_request_group_id']

    collection = ArchivedCall.get_collection()
    cursor = collection.find(query)
    return cursor

# reaper functions -------------------------------------------------------------

def start_reaper_thread():
    """
    Run a reaper thread in the background, removing expired archived tasks from
    the database.
    """

    def _reaper_thread_main():
        while True:
            purge_archived_tasks()
            time.sleep(1800) # sleep for 30 minutes

    thread = threading.Thread(target=_reaper_thread_main)
    thread.setDaemon(True)
    thread.start()

def purge_archived_tasks():
    """
    Remove archived tasks from the database that have expired.
    """
    archived_call_lifetime = pulp_config.config.getint('tasks', 'archived_call_lifetime')

    delta = datetime.timedelta(hours=archived_call_lifetime)
    now = datetime.datetime.now(tz=dateutils.utc_tz())
    expired_timestamp = dateutils.datetime_to_utc_timestamp(now - delta)

    collection = ArchivedCall.get_collection()
    collection.remove({'timestamp': {'$lte': expired_timestamp}}, safe=True)


