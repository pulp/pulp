#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import bson
import functools
import pickle
import time

from celery.schedules import schedule

from pulp.common import dateutils
from pulp.server.db import connection


def migrate(*args, **kwargs):
    schedule_collection = connection.get_collection('scheduled_calls')
    importer_collection = connection.get_collection('repo_importers')
    distributor_collection = connection.get_collection('repo_distributors')

    map(functools.partial(convert_schedule, schedule_collection.save), schedule_collection.find())
    move_scheduled_syncs(importer_collection, schedule_collection)
    move_scheduled_publishes(distributor_collection, schedule_collection)


def move_scheduled_syncs(importer_collection, schedule_collection):
    """
    Searches importers to determine which have references to a schedule,
    removes those references, and adds the appropriate resource_id to the
    schedule.

    :param importer_collection: collection where importers are stored
    :type  importer_collection: pulp.server.db.connection.PulpCollection
    :param schedule_collection: collection where schedules are stored
    :type  schedule_collection: pulp.server.db.connection.PulpCollection
    """

    # iterate over all importers looking for those with scheduled syncs
    for importer in importer_collection.find(fields=['scheduled_syncs', 'id', 'repo_id']):
        scheduled_syncs = importer.get('scheduled_syncs')
        if scheduled_syncs is None:
            continue

        # add the new resource_id to the appropriate schedules
        resource_id = 'pulp:importer:%s:%s' % (importer['repo_id'], importer['id'])
        update_spec = {'$set': {'resource': resource_id}}
        for schedule_id in scheduled_syncs:
            schedule_collection.update({'_id': bson.ObjectId(schedule_id)}, update_spec)

    # remove this field from all importers
    importer_collection.update({}, {'$unset': {'scheduled_syncs': ''}}, multi=True)


def move_scheduled_publishes(distributor_collection, schedule_collection):
    """
    Searches distributors to determine which have references to a schedule,
    removes those references, and adds the appropriate resource_id to the
    schedule.

    :param distributor_collection:  collection where distributors are stored
    :type  distributor_collection:  pulp.server.db.connection.PulpCollection
    :param schedule_collection:     collection where schedules are stored
    :type  schedule_collection:     pulp.server.db.connection.PulpCollection
    """

    # iterate over all distributors looking for those with scheduled publishes
    for distributor in distributor_collection.find(fields=['scheduled_publishes', 'id', 'repo_id']):
        scheduled_publishes = distributor.get('scheduled_publishes')
        if scheduled_publishes is None:
            continue

        # add the new resource_id to the appropriate schedules
        resource_id = 'pulp:distributor:%s:%s' % (distributor['repo_id'], distributor['id'])
        update_spec = {'$set': {'resource': resource_id}}
        for schedule_id in scheduled_publishes:
            schedule_collection.update({'_id': bson.ObjectId(schedule_id)}, update_spec)

    # remove this field from all distributors
    distributor_collection.update({}, {'$unset': {'scheduled_publishes': ''}}, multi=True)


def convert_schedule(save_func, call):
    """
    Converts one scheduled call from the old schema to the new

    :param save_func:   a function that takes one parameter, a dictionary that
                        represents the scheduled call in its new schema. This
                        function should save the call to the database.
    :type  save_func:   function
    :param call:        dictionary representing the scheduled call in its old
                        schema
    :type  call:        dict
    """
    call.pop('call_exit_states', None)
    call['total_run_count'] = call.pop('call_count')

    call['iso_schedule'] = call['schedule']
    interval, start_time, occurrences = dateutils.parse_iso8601_interval(call['schedule'])
    # this should be a pickled instance of celery.schedules.schedule
    call['schedule'] = pickle.dumps(schedule(interval))

    call_request = call.pop('serialized_call_request')
    # we are no longer storing these pickled.
    # these are cast to a string because python 2.6 sometimes fails to
    # deserialize json from unicode.
    call['args'] = pickle.loads(str(call_request['args']))
    call['kwargs'] = pickle.loads(str(call_request['kwargs']))
    # keeping this pickled because we don't really know how to use it yet
    call['principal'] = call_request['principal']
    # this always get calculated on-the-fly now
    call.pop('next_run', None)
    first_run = call['first_run'].replace(tzinfo=dateutils.utc_tz())
    call['first_run'] = dateutils.format_iso8601_datetime(first_run)
    last_run = call.pop('last_run')
    if last_run:
        last_run_at = last_run.replace(tzinfo=dateutils.utc_tz())
        call['last_run_at'] = dateutils.format_iso8601_datetime(last_run_at)
    else:
        call['last_run_at'] = None
    call['task'] = NAMES_TO_TASKS[call_request['callable_name']]

    # this is a new field that is used to determine when the scheduler needs to
    # re-read the collection of schedules.
    call['last_updated'] = time.time()

    # determine if this is a consumer-related schedule, which we can only identify
    # by the consumer resource tag. If it is, save that tag value in the new
    # "resource" field, which is the new way that we will identify the
    # relationship between a schedule and some other object. This is not
    # necessary for repos, because we have a better method above for identifying
    # them (move_scheduled_syncs).
    tags = call_request.get('tags', [])
    for tag in tags:
        if tag.startswith('pulp:consumer:'):
            call['resource'] = tag
            break

    save_func(call)


# keys are old names, values are new names
# these are the only tasks that have been possible to schedule
NAMES_TO_TASKS = {
    'publish_itinerary': 'pulp.server.tasks.repository.publish',
    'sync_with_auto_publish_itinerary': 'pulp.server.tasks.repository.sync_with_auto_publish',
    'consumer_content_install_itinerary': 'pulp.server.tasks.consumer.install_content',
    'consumer_content_update_itinerary': 'pulp.server.tasks.consumer.update_content',
    'consumer_content_uninstall_itinerary': 'pulp.server.tasks.consumer.uninstall_content',
}


# in case someone needs to apply this manually
if __name__ == '__main__':
    connection.initialize()
    migrate()
