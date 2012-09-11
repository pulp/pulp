# -*- coding: utf-8 -*-

# Copyright © 2010-2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


import logging
import pickle

from pulp.server.db.model import  dispatch
from pulp.server.managers.auth.principal import SystemUser, _SYSTEM_LOGIN

_log = logging.getLogger('pulp')


version = 2


def _pickled_system_user():
    system_user = SystemUser()
    return pickle.dumps(system_user)


def _migrate_queued_calls():
    collection = dispatch.QueuedCall.get_collection()
    collection.update({}, {'serialized_call_request.principal': _pickled_system_user()}, safe=True, multi=True)


def _migrate_scheduled_calls():
    collection = dispatch.ScheduledCall.get_collection()
    collection.update({}, {'serialized_call_request.principal': _pickled_system_user()}, safe=True, multi=True)


def _migrate_archived_calls():
    collection = dispatch.ArchivedCall.get_collection()
    collection.update({}, {'serialized_call_request.principal': _pickled_system_user(), 'serialized_call_report.principal_login': _SYSTEM_LOGIN}, safe=True, multi=True)


def migrate():
    _log.info('migration to data model version %d started' % version)
    _migrate_queued_calls()
    _migrate_scheduled_calls()
    _migrate_archived_calls()
    _log.info('migration to data model version %d complete' % version)
