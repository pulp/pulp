# -*- coding: utf-8 -*-
#
# Copyright © 2012-2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from pulp.server.db.model.dispatch import ArchivedCall

# public api -------------------------------------------------------------------

def archive_call(call_request, call_report):
    """
    Store a completed call request in the database.

    :param call_request: call request to store
    :type call_request: pulp.server.dispatch.call.CallRequest
    :param call_report: call report corresponding to the call request
    :type call_report: pulp.server.dispatch.call.CallReport
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

    :return: (possibly empty) mongo collection cursor containing the matching archived calls
    :rtype: pymongo.cursor.Cursor
    """
    query = {}
    if 'call_request_id' in criteria:
        query['serialized_call_request.id'] = criteria['call_request_id']
    if 'call_request_group_id' in criteria:
        query['serialized_call_request.group_id'] = criteria['call_request_group_id']

    collection = ArchivedCall.get_collection()
    cursor = collection.find(query)
    return cursor

