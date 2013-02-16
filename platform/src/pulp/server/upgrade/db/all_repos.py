# -*- coding: utf-8 -*-
# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
This module handles upgrading the pieces of repositories that apply to
both v1 types, such as repo groups and sync schedules.
"""

from datetime import datetime

from pulp.common import dateutils
from pulp.common.tags import resource_tag
from pulp.server.compat import ObjectId
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch.call import CallRequest
from pulp.server.itineraries.repo import sync_with_auto_publish_itinerary
from pulp.server.managers.auth.user.system import SystemUser
from pulp.server.upgrade.model import UpgradeStepReport


def upgrade(v1_database, v2_database):

    report = UpgradeStepReport()

    group_success = _repo_groups(v1_database, v2_database, report)
    sync_schedule_success = _sync_schedules(v1_database, v2_database, report)

    report.success = (group_success and sync_schedule_success)
    return report


def _repo_groups(v1_database, v2_database, report):
    v1_coll = v1_database.repos
    v2_coll = v2_database.repo_groups

    # Idempotency: Two-fold. All group IDs will be collected and groups created
    # from those IDs, using the ID to determine if it already exists. The second
    # is the addition of repo IDs to the group, which will be handled by mongo.

    # I should probably use a map reduce here, but frankly this is simpler and
    # I'm not terribly worried about either the mongo performance or memory
    # consumption from the approach below.
    repo_and_group_ids = [(x['id'], x['groupid']) for x in v1_coll.find({}, {'id' : 1, 'groupid' : 1, 'content_types' : 1})
                          if x.has_key('groupid')]
    repo_ids_by_group = {}
    for repo_id, group_id_list in repo_and_group_ids:

        # Yes, "groupid" in the repo is actually a list. Ugh.
        for group_id in group_id_list:
            l = repo_ids_by_group.setdefault(group_id, [])
            l.append(repo_id)

    v1_group_ids = repo_ids_by_group.keys()
    existing_v2_group_ids = v2_coll.find({'id' : {'$nin' : v1_group_ids}})

    missing_group_ids = set(v1_group_ids) - set(existing_v2_group_ids)

    new_groups = []
    for group_id in missing_group_ids:
        new_group = {
            '_id' : ObjectId(),
            'id' : group_id,
            'display_name' : None,
            'description' : None,
            'repo_ids' : [],
            'notes' : {},
            }
        new_groups.append(new_group)

    if new_groups:
        v2_coll.insert(new_groups, safe=True)

    for group_id, repo_ids in repo_ids_by_group.items():
        v2_coll.update({'id' : group_id}, {'$addToSet' : {'repo_ids' : {'$each' : repo_ids}}})

    return True


def _sync_schedules(v1_database, v2_database, report):
    v1_repo_collection = v1_database.repos
    v2_repo_importer_collection = v2_database.repo_importers
    v2_scheduled_call_collection = v2_database.scheduled_calls

    # ugly hack to find out which repos have already been scheduled
    # necessary because $size is not a meta-query and doesn't support $gt, etc
    repos_without_schedules = v2_repo_importer_collection.find(
        {'scheduled_syncs': {'$size': 0}}, fields=['repo_id'])

    repo_ids_without_schedules = [r['repo_id'] for r in repos_without_schedules]

    repos_with_schedules = v2_repo_importer_collection.find(
        {'repo_id': {'$nin': repo_ids_without_schedules}}, fields=['repo_id'])

    repo_ids_with_schedules = [r['repo_id'] for r in repos_with_schedules]

    repos_to_schedule = v1_repo_collection.find(
        {'id': {'$nin': repo_ids_with_schedules}, 'sync_schedule': {'$ne': None}},
        fields=['id', 'sync_schedule', 'sync_options', 'last_sync'])

    for repo in repos_to_schedule:

        if repo['id'] not in repo_ids_without_schedules:
            report.error('Repository [%s] not found in the v2 database.'
                         'sync scheduling being canceled.' % repo['id'])
            return False

        args = [repo['id']]
        kwargs = {'overrides': {}}
        call_request = CallRequest(sync_with_auto_publish_itinerary, args, kwargs, principal=SystemUser())

        scheduled_call_document = {
            '_id': ObjectId(),
            'id': None,
            'serialized_call_request': None,
            'schedule': repo['sync_schedule'],
            'failure_threshold': None,
            'consecutive_failures': 0,
            'first_run': None,
            'last_run': dateutils.to_naive_utc_datetime(dateutils.parse_iso8601_datetime(repo['last_sync'])),
            'next_run': None,
            'remaining_runs': None,
            'enabled': True}

        scheduled_call_document['id'] = str(scheduled_call_document['_id'])

        schedule_tag = resource_tag(dispatch_constants.RESOURCE_SCHEDULE_TYPE, scheduled_call_document['id'])
        call_request.tags.append(schedule_tag)
        scheduled_call_document['serialized_call_request'] = call_request.serialize()

        if isinstance(repo['sync_options'], dict):
            scheduled_call_document['failure_threshold'] = repo['sync_options'].get('failure_threshold', None)

        interval, start, recurrences = dateutils.parse_iso8601_interval(scheduled_call_document['schedule'])
        scheduled_call_document['first_run'] = start or datetime.utcnow()
        scheduled_call_document['remaining_runs'] = recurrences

        scheduled_call_document['next_run'] = _calculate_next_run(scheduled_call_document)

        v2_scheduled_call_collection.insert(scheduled_call_document, safe=True)
        v2_repo_importer_collection.update({'repo_id': repo['id']},
                                           {'$push': {'scheduled_syncs': scheduled_call_document['id']}},
                                           safe=True)

    return True


def _calculate_next_run(scheduled_call):
    # rip-off from scheduler module
    if scheduled_call['remaining_runs'] == 0:
        return None
    last_run = scheduled_call['last_run']
    if last_run is None:
        return scheduled_call['first_run']
    now = datetime.utcnow()
    interval = dateutils.parse_iso8601_interval(scheduled_call['schedule'])[0]
    next_run = last_run
    while next_run < now:
        next_run = dateutils.add_interval_to_datetime(interval, next_run)
    return next_run
