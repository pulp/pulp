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

from collections import namedtuple
from gettext import gettext as _
import logging
import threading
import time

from celery import beat
from celery.result import AsyncResult
import itertools

from pulp.server.async.celery_instance import celery as app
from pulp.server.db.model.dispatch import ScheduledCall, ScheduleEntry
from pulp.server.managers.schedule import utils


_logger = logging.getLogger(__name__)


class FailureWatcher(object):
    _default_pop = (None, None, None)
    WatchedTask = namedtuple('WatchedTask', ['timestamp', 'schedule_id', 'has_failure'])
    # how long we will track a task from the time it gets queued.
    ttl = 60*60*4  # 4 hours

    def __init__(self):
        self._watches = {}

    def trim(self):
        """
        Removes tasks from our collections of tasks that are being watched for
        failure by looking for tasks that have been in the collection for more
        than self.ttl seconds.
        """
        oldest_allowed = int(time.time()) - self.ttl
        for task_id in (task_id for task_id, watch in self._watches.items()
                        if watch.timestamp < oldest_allowed):
            self._watches.pop(task_id, None)

    def add(self, task_id, schedule_id, has_failure):
        """
        Add a task to our collection of tasks to watch.

        :param task_id:     UUID of the task that was just queued
        :type  task_id:     basestring
        :param schedule_id: ID of the schedule that caused the task to be queued
        :type  schedule_id: basestring
        :param has_failure: True iff the schedule in question has at least one
                            consecutive failure currently recorded. If True, the
                            success handler can ignore this task.
        :type  has_failure: bool
        """
        self._watches[task_id] = self.WatchedTask(int(time.time()), schedule_id, has_failure)

    def pop(self, task_id):
        """
        removes the entry for the requested task_id and returns its schedule_id
        and has_failure attributes

        :param task_id:     UUID of a task
        :type  task_id:     basestring
        :return:            2-item list of [schedule_id, has_failure], where
                            schedule_id and has_failure will be None if the
                            task_id is not found.
        :rtype:             [basestring, bool]
        """
        return self._watches.pop(task_id, self._default_pop)[1:]

    def monitor_events(self):
        """
        Receives events from celery and matches each with the appropriate
        handler function. This will not return, and thus should be called in
        its own thread.
        """
        with app.connection() as connection:
            recv = app.events.Receiver(connection, handlers={
                'task-failed': self.handle_failed_task,
                'task-succeeded': self.handle_succeeded_task,
            })
            recv.capture(limit=None, timeout=None, wakeup=False)

    def handle_succeeded_task(self, event):
        """
        Celery event handler for succeeded tasks. This will check if we are
        watching the task for failure, and if so, ensure that the corresponding
        schedule's failure count either already was 0 when the task was queued
        or that it gets reset to 0.

        :param event:   dictionary of poorly-documented data about a celery task.
                        At a minimum, this method depends on the key 'uuid'
                        being present and representing the task's ID.
        :type event:    dict
        """
        event_id = event['uuid']
        schedule_id, has_failure = self.pop(event_id)
        if schedule_id:
            return_value = AsyncResult(event_id, app=app).result
            if isinstance(return_value, AsyncResult):
                _logger.debug(_('watching child event %(id)s for failure') % {'id': return_value.id})
                self.add(return_value.id, schedule_id, has_failure)
            elif has_failure:
                _logger.info(_('resetting consecutive failure count for schedule %(id)s')
                             % {'id': schedule_id})
                utils.reset_failure_count(schedule_id)

    def handle_failed_task(self, event):
        """
        Celery event handler for failed tasks. This will check if we are
        watching the task for failure, and if so, increments the corresponding
        schedule's failure count. If it has met or exceeded its failure
        threshold, the schedule will be disabled.

        :param event:   dictionary of poorly-documented data about a celery task.
                        At a minimum, this method depends on the key 'uuid'
                        being present and representing the task's ID.
        :type event:    dict
        """
        schedule_id, has_failure = self.pop(event['uuid'])
        if schedule_id:
            _logger.info(_('incrementing consecutive failure count for schedule %(id)s') % {'id': schedule_id})
            utils.increment_failure_count(schedule_id)

    def __len__(self):
        return len(self._watches)


class Scheduler(beat.Scheduler):
    Entry = ScheduleEntry

    # the superclass reads this attribute, which is the maximum number of seconds
    # that will ever elapse before the scheduler looks for new or changed schedules.
    max_interval = 90

    def __init__(self, *args, **kwargs):
        self._schedule = None
        self._failure_watcher = FailureWatcher()
        self._loaded_from_db_count = 0
        # start monitoring events in a thread
        thread = threading.Thread(target=self._failure_watcher.monitor_events)
        thread.daemon = True
        thread.start()

        super(Scheduler, self).__init__(*args, **kwargs)

    def tick(self):
        """
        Superclass runs a tick, that is one iteration of the scheduler. Executes
        all due tasks.

        This method adds a call to trim the failure watcher.

        :return:    number of seconds before the next tick should run
        :rtype:     float
        """
        ret = super(Scheduler, self).tick()
        self._failure_watcher.trim()
        return ret

    def setup_schedule(self):
        """
        This loads enabled schedules from the database and adds them to the
        "_schedule" dictionary as instances of celery.beat.ScheduleEntry
        """
        _logger.debug(_('loading schedules from app'))
        self._schedule = {}
        for key, value in self.app.conf.CELERYBEAT_SCHEDULE.iteritems():
            self._schedule[key] = beat.ScheduleEntry(**dict(value, name=key))

        # include a "0" as the default in case there are no schedules to load
        update_timestamps = [0]

        _logger.debug(_('loading schedules from DB'))
        ignored_db_count = 0
        self._loaded_from_db_count = 0
        for call in itertools.imap(ScheduledCall.from_db, utils.get_enabled()):
            if call.remaining_runs == 0:
                _logger.debug(_('ignoring schedule with 0 remaining runs: %(id)s') % {'id': call.id})
                ignored_db_count += 1
            else:
                self._schedule[call.id] = call.as_schedule_entry()
                update_timestamps.append(call.last_updated)
                self._loaded_from_db_count += 1

        _logger.debug('loaded %(count)d schedules' % {'count': self._loaded_from_db_count})

        self._most_recent_timestamp = max(update_timestamps)

    @property
    def schedule_changed(self):
        """
        Looks at the update timestamps in the database to determine if there
        are new or modified schedules.

        Indexing should make this very fast.

        :return:    True iff the set of enabled scheduled calls has changed
                    in the database.
        :rtype:     bool
        """
        if utils.get_enabled().count() != self._loaded_from_db_count:
            logging.debug(_('number of enabled schedules has changed'))
            return True

        if utils.get_updated_since(self._most_recent_timestamp).count() > 0:
            logging.debug(_('one or more enabled schedules has been updated'))
            return True

        return False

    @property
    def schedule(self):
        """
        :return:    dictionary where keys are schedule ids and values are
                    instances of celery.beat.ScheduleEntry. These instances are
                    the schedules currently in active use by the scheduler.
        :rtype:     dict
        """
        if self._schedule is None or self.schedule_changed:
            self.setup_schedule()

        return self._schedule

    def add(self, **kwargs):
        """
        This class does not support adding entries in-place. You must add new
        entries to the database, and they will be picked up automatically.
        """
        raise NotImplementedError

    def apply_async(self, entry, publisher=None, **kwargs):
        """
        The superclass calls apply_async on the task that is referenced by the
        entry. This method also adds the queued task to our list of tasks to
        watch for failure if the task has a failure threshold.

        :param entry:       schedule entry whose task should be queued.
        :type  entry:       celery.beat.ScheduleEntry
        :param publisher:   unknown. used by celery but not documented
        :type kwargs:       dict
        :return:
        """
        result = super(Scheduler, self).apply_async(entry, publisher, **kwargs)
        if isinstance(entry, ScheduleEntry) and entry._scheduled_call.failure_threshold:
            has_failure = bool(entry._scheduled_call.consecutive_failures)
            self._failure_watcher.add(result.id, entry.name, has_failure)
            _logger.debug(_('watching task %s') % {'id': result.id})
        return result
