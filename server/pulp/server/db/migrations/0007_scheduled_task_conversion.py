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
import functools
import pickle
import bson

import celery
from celery.schedules import schedule
import time

from pulp.common import dateutils
from pulp.server.async.tasks import Task
from pulp.server.compat import json, json_util
from pulp.server.db import connection
from pulp.server.db.model.dispatch import ScheduledCall
from pulp.server.itineraries import repo
from pulp.server.itineraries.repo import dummy_itinerary


def migrate(*args, **kwargs):
    collection = connection.get_collection('scheduled_calls')

    map(functools.partial(convert, collection.save), collection.find())


def convert(save_func, call):
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

    call['task'] = dummy_itinerary.name
    call['last_updated'] = time.time()

    save_func(call)
    foo = bson.BSON.decode(bson.BSON.encode(call))
    print json.dumps(foo, indent=4, default=json_util.default)
    print ScheduledCall.from_db(call)


if __name__ == '__main__':
    connection.initialize()
    migrate()


FOO = """
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