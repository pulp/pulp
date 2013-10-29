#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
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
from pulp.server.compat import json, json_util
from pulp.server.db import connection
from pulp.server.db.model.dispatch import ScheduledCall


def migrate(*args, **kwargs):
    schedule_collection = connection.get_collection('scheduled_calls')
    map(functools.partial(convert_schedules, schedule_collection.save), schedule_collection.find())

    importer_collection = connection.get_collection('repo_importers')
    distributor_collection = connection.get_collection('repo_distributors')
    move_scheduled_syncs(importer_collection, schedule_collection)
    move_scheduled_publishes(distributor_collection, schedule_collection)


def move_scheduled_syncs(importer_collection, schedule_collection):
    for importer in importer_collection.find(fields=['scheduled_syncs', 'id', 'repo_id']):
        scheduled_syncs = importer.get('scheduled_syncs')
        if scheduled_syncs is None:
            continue

        resource_id = 'pulp:importer:%s:%s' % (importer['repo_id'], importer['id'])
        update_spec = {'$set': {'resource': resource_id}}
        for schedule_id in scheduled_syncs:
            schedule_collection.update({'_id': bson.ObjectId(schedule_id)}, update_spec)

    # remove this field from all importers
    importer_collection.update({}, {'$unset': {'scheduled_syncs': ''}})


def move_scheduled_publishes(distributor_collection, schedule_collection):
    for distributor in distributor_collection.find(fields=['scheduled_publishes', 'id', 'repo_id']):
        scheduled_publishes = distributor.get('scheduled_publishes')
        if scheduled_publishes is None:
            continue

        resource_id = 'pulp:distributor:%s:%s' % (distributor['repo_id'], distributor['id'])
        update_spec = {'$set': {'resource': resource_id}}
        for schedule_id in scheduled_publishes:
            schedule_collection.update({'_id': bson.ObjectId(schedule_id)}, update_spec)

    # remove this field from all distributors
    distributor_collection.update({}, {'$unset': {'scheduled_publishes': ''}})


def convert_schedules(save_func, call):
    del call['call_exit_states']
    call['total_run_count'] = call.pop('call_count')

    call['iso_schedule'] = call['schedule']
    interval, start_time, occurrences = dateutils.parse_iso8601_interval(call['schedule'])
    call['schedule'] = pickle.dumps(schedule(interval))

    call_request = call.pop('serialized_call_request')
    call['args'] = pickle.loads(call_request['args'])
    call['kwargs'] = pickle.loads(call_request['kwargs'])
    # pickled string
    call['principal'] = call_request['principal']
    next_run = call['next_run'].replace(tzinfo=dateutils.utc_tz())
    call['next_run'] = dateutils.format_iso8601_datetime(next_run)
    first_run = call['first_run'].replace(tzinfo=dateutils.utc_tz())
    call['first_run'] = dateutils.format_iso8601_datetime(first_run)
    last_run_at = call.pop('last_run').replace(tzinfo=dateutils.utc_tz())
    call['last_run_at'] = dateutils.format_iso8601_datetime(last_run_at)

    call['task'] = NAMES_TO_TASKS[call_request['callable_name']]

    call['last_updated'] = time.time()

    # determine if this is a consumer-related schedule, which we can only identify
    # by the consumer resource tag. If it is, save that tag value in the new
    # "resource" field, which is the new way that we will identify the
    # relationship between a schedule and some other object.
    tags = call_request.get('tags', [])
    for tag in tags:
        if tag.startswith('pulp:consumer:'):
            call['resource'] = tag
            break

    save_func(call)
    foo = bson.BSON.decode(bson.BSON.encode(call))
    print json.dumps(foo, indent=4, default=json_util.default)
    print ScheduledCall.from_db(call)


NAMES_TO_TASKS = {
    'publish_itinerary': 'pulp.server.tasks.repository.publish',
    'sync_with_auto_publish_itinerary': 'pulp.server.tasks.repository.sync_with_auto_publish',
    'repo_delete_itinerary': 'pulp.server.tasks.repository.delete',
    'distributor_delete_itinerary': 'pulp.server.tasks.repository.distributor_delete',
    'distributor_update_itinerary': 'pulp.server.tasks.repository.distributor_update',
    'bind_itinerary': 'pulp.server.tasks.consumer.bind',
    'unbind_itinerary': 'pulp.server.tasks.consumer.unbind',
    'forced_unbind_itinerary': 'pulp.server.tasks.consumer.force_unbind',
    'consumer_content_install_itinerary': 'pulp.server.tasks.consumer.install_content',
    'consumer_content_update_itinerary': 'pulp.server.tasks.consumer.update_content',
    'consumer_content_uninstall_itinerary': 'pulp.server.tasks.consumer.uninstall_content',
    'consumer_group_bind_itinerary': 'pulp.server.tasks.consumer_group.bind',
    'consumer_group_unbind_itinerary': 'pulp.server.tasks.consumer_group.unbind',
    'consumer_group_content_install_itinerary': 'pulp.server.tasks.consumer_group.install_content',
    'consumer_group_content_update_itinerary': 'pulp.server.tasks.consumer_group.update_content',
    'consumer_group_content_uninstall_itinerary': 'pulp.server.tasks.consumer_group.uninstall_content',
}


if __name__ == '__main__':
    connection.initialize()
    migrate()


OLD_FORMAT = """
{
	"_id" : ObjectId("525844f3e19a001d665f97ea"),
	"serialized_call_request" : {
		"control_hooks" : "(lp0\nNa.",
		"weight" : 0,
		"tags" : [
			"pulp:schedule:525844f3e19a001d665f97ea"
		],
		"archive" : false,
		"args" : "(lp0\nVdemo\np1\naVpuppet_distributor\np2\na.",
		"callable_name" : "publish_itinerary",
		"schedule_id" : null,
		"asynchronous" : false,
		"kwargs" : "(dp0\nS'overrides'\np1\n(dp2\ns.",
		"execution_hooks" : "(lp0\n(lp1\na(lp2\na(lp3\na(lp4\na(lp5\na(lp6\na(lp7\na.",
		"call" : "cpulp.server.itineraries.repo\npublish_itinerary\np0\n.",
		"group_id" : null,
		"id" : "0220e35a-5dcc-4e0b-a8c7-f332080c0c96",
		"resources" : {

		},
		"principal" : "(dp0\nV_id\np1\nccopy_reg\n_reconstructor\np2\n(cbson.objectid\nObjectId\np3\nc__builtin__\nobject\np4\nNtp5\nRp6\nS'R \\xab\\x06\\xe1\\x9a\\x00\\x10\\xe1i\\x05\\x89'\np7\nbsVname\np8\nVadmin\np9\nsVroles\np10\n(lp11\nVsuper-users\np12\nasV_ns\np13\nVusers\np14\nsVlogin\np15\nVadmin\np16\nsVpassword\np17\nVV76Yol1XYgM=,S/G6o5UyMrn0xAwbQCqFcrXnfXTh84RWhunanCDkSCo=\np18\nsVid\np19\nV5220ab06e19a0010e1690589\np20\ns."
	},
	"next_run" : ISODate("2013-10-12T13:00:00Z"),
	"remaining_runs" : null,
	"first_run" : ISODate("2013-10-12T13:00:00Z"),
	"schedule" : "2013-10-01T13:00:00Z/P1D",
	"_ns" : "scheduled_calls",
	"enabled" : true,
	"last_run" : null,
	"failure_threshold" : null,
	"call_exit_states" : [ ],
	"consecutive_failures" : 0,
	"id" : "525844f3e19a001d665f97ea",
	"call_count" : 0
}
"""