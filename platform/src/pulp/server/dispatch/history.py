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

from pulp.server.db.model.dispatch import ArchivedCall

# public api -------------------------------------------------------------------

def archive_call(call_request, call_report):
    archived_call = ArchivedCall(call_request, call_report)
    collection = ArchivedCall.get_collection()
    collection.insert(archived_call, safe=True)


def find_archived_calls(**criteria):
    query = {}
    if 'task_id' in criteria:
        query['serialized_call_report.task_id'] = criteria['task_id']
    if 'task_group_id' in criteria:
        query['serialized_call_report.task_group_id'] = criteria['task_group_id']
    if 'state' in criteria:
        query['serialized_call_report.state'] = criteria['state']
    if 'call_name' in criteria:
        call_name = callable_name(criteria.get('class_name'), criteria['call_name'])
        query['serialized_call_request.callable_name'] = call_name
    # XXX allow args, kwargs, and resources?
    if 'tags' in criteria:
        query['serialized_call_request.tags'] = {'$in': criteria['tags']}

    collection = ArchivedCall.get_collection()
    cursor = collection.find(query)
    return cursor

# utility functions ------------------------------------------------------------

def callable_name(class_name=None, call_name=None):
    assert call_name is not None
    if class_name is None:
        return call_name
    return '.'.join((class_name, call_name))


