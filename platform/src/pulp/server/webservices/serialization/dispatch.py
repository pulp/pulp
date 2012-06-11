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

from datetime import datetime

from pulp.common import dateutils


def task_href(call_report):
    if call_report.task_id is None:
        return {}
    return {'_href': '/pulp/api/v2/tasks/%s/' % call_report.task_id}


def job_href(call_report):
    if call_report.job_id is None:
        return {}
    return {'_href': '/pulp/api/v2/jobs/%s/' % call_report.job_id}


def scheduled_call_obj(scheduled_call):
    obj = {
        '_id': str(scheduled_call['_id']),
        '_href': None, # should be replaced by the caller!
        'schedule': scheduled_call['schedule'],
        'failure_threshold': scheduled_call['failure_threshold'],
        'enabled': scheduled_call['enabled'],
        'consecutive_failures': scheduled_call['consecutive_failures'],
        'remaining_runs': scheduled_call['remaining_runs'],
        'first_run': None,
        'last_run': None,
        'next_run': None,
    }
    for run_time_field in ('first_run', 'last_run', 'next_run'):
        run_time = scheduled_call[run_time_field]
        if isinstance(run_time, datetime):
            utc_run_time = run_time.replace(tzinfo=dateutils.utc_tz())
            obj[run_time_field] = dateutils.format_iso8601_datetime(utc_run_time)
    return obj


def scheduled_sync_obj(scheduled_call):
    obj = scheduled_call_obj(scheduled_call)
    obj['override_config'] = scheduled_call['call_request'].kwargs['sync_config_override']
    return obj


def scheduled_publish_obj(scheduled_call):
    obj = scheduled_call_obj(scheduled_call)
    obj['override_config'] = scheduled_call['call_request'].kwargs['publish_config_override']
    return obj
