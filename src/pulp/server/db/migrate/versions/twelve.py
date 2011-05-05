# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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

import logging
from datetime import datetime

from pulp.common import dateutils
from pulp.server.db.model.audit import Event
from pulp.server.db.model.cds import CDSHistoryEvent
from pulp.server.db.model.resource import ConsumerHistoryEvent


_log = logging.getLogger('pulp')

version = 12


def _from_utc_timestamp_to_iso8601(timestamp):
    try:
        raw = datetime.utcfromtimestamp(float(timestamp))
        utc = raw.replace(tzinfo=dateutils.utc_tz())
        return dateutils.format_iso8601_datetime(utc)
    except:
        # screw it, they're just timestamps after all...
        return None


def _migrate_timestamps(collection):
    for item in collection:
        item['timestamp'] = _from_utc_timestamp_to_iso8601(item['timestamp'])
        collection.save(item, safe=True)


def _migrate_auditing_events():
    _migrate_timestamps(Event.get_collection())


def _migrate_cds_history_events():
    _migrate_timestamps(CDSHistoryEvent.get_collection())


def _migrate_consumer_history_events():
    _migrate_timestamps(ConsumerHistoryEvent.get_collection())


def migrate():
    _log.info('migration to data model version %d started' % version)
    _migrate_auditing_events()
    _migrate_cds_history_events()
    _migrate_consumer_history_events()
    _log.info('migration to data model version %d complete' % version)
