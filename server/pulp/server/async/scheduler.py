# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software;
# if not, see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import logging

from celery import beat

from pulp.server.db.model.dispatch import ScheduledCall, ScheduleEntry


collection = ScheduledCall.get_collection()


logger = logging.getLogger(__name__)


class Scheduler(beat.Scheduler):
    Entry = ScheduleEntry

    max_interval = 90

    def __init__(self, *args, **kwargs):
        self._schedule = None
        super(Scheduler, self).__init__(*args, **kwargs)

    def setup_schedule(self):
        logger.debug('loading schedules from DB')

        # load schedules from DB
        self._schedule = {}
        update_timestamps = []
        for call in collection.find({'enabled': True}):
            call = ScheduledCall.from_db(call)
            self._schedule[call.id] = call.as_schedule_entry()
            update_timestamps.append(call.last_updated)

        logger.debug('loaded %d schedules' % len(self._schedule))

        self._most_recent_timestamp = max(update_timestamps)

    @property
    def schedule_changed(self):
        """
        :return:    True iff the set of enabled scheduled calls has changed
                    in the database.
        :rtype:     bool
        """
        if collection.find({'enabled': True}).count() != len(self._schedule):
            logging.debug('number of enabled schedules has changed')
            return True

        query = {
            'enabled': True,
            'last_updated': {'$gt': self._most_recent_timestamp},
        }
        if collection.find(query).count() > 0:
            logging.debug('one or more enabled schedules has been updated')
            return True

        return False

    @property
    def schedule(self):
        if self._schedule is None or self.schedule_changed:
            self.setup_schedule()

        return self._schedule

    def add(self, **kwargs):
        """
        This class does not support adding entries in-place. You must add new
        entries to the database, and they will be picked up automatically.
        """
        raise NotImplemented
