# -*- coding: utf-8 -*-
#
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

import logging
from datetime import datetime, timedelta

from pulp.common import dateutils
from pulp.server.db.model.audit import Event
from pulp.server.db.model.cds import CDS, CDSHistoryEvent
from pulp.server.db.model.resource import ConsumerHistoryEvent, Repo


_log = logging.getLogger('pulp')

version = 12

# timestamp migration ----------------------------------------------------------

def _from_utc_timestamp_to_iso8601(timestamp):
    try:
        raw = datetime.utcfromtimestamp(float(timestamp))
        utc = raw.replace(tzinfo=dateutils.utc_tz())
        return dateutils.format_iso8601_datetime(utc)
    except:
        # conversion didn't work, assume it's already in the right form...
        return timestamp


def _from_datetime_to_iso8601(dt):
    dt = dt.replace(tzinfo=dateutils.local_tz())
    return dateutils.format_iso8601_datetime(dt)


def _migrate_timestamps(collection):
    for item in collection.find():
        timestamp = item['timestamp']
        if isinstance(timestamp, unicode):
            item['timestamp'] = _from_utc_timestamp_to_iso8601(timestamp)
        elif isinstance(timestamp, datetime):
            item['timestamp'] = _from_datetime_to_iso8601(timestamp)
        collection.save(item, safe=True)

# schedule migration -----------------------------------------------------------

def _from_object_to_is8601_interval(obj):
    if obj is None:
        return None
    interval = timedelta(**obj['interval'])
    start_time = obj.get('start_time')
    if start_time is not None:
        start_time = datetime(**start_time)
    runs = obj.get('runs')
    return dateutils.format_iso8601_interval(interval, start_time, runs)


def _migrate_sync_schedule(collection):
    for item in collection.find():
        schedule = item['sync_schedule']
        if isinstance(schedule, basestring):
            continue
        item['sync_schedule'] = _from_object_to_is8601_interval(schedule)
        collection.save(item, safe=True)

# collection migration ---------------------------------------------------------

def _migrate_auditing_events():
    _migrate_timestamps(Event.get_collection())


def _migrate_cds():
    _migrate_sync_schedule(CDS.get_collection())


def _migrate_cds_history_events():
    _migrate_timestamps(CDSHistoryEvent.get_collection())


def _migrate_consumer_history_events():
    _migrate_timestamps(ConsumerHistoryEvent.get_collection())


def _migrate_repos():
    _migrate_sync_schedule(Repo.get_collection())


def migrate():
    _log.info('migration to data model version %d started' % version)
    _migrate_auditing_events()
    _migrate_cds()
    _migrate_cds_history_events()
    _migrate_consumer_history_events()
    _migrate_repos()
    _log.info('migration to data model version %d complete' % version)
