# -*- coding: utf-8 -*-
# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os
from okaara import prompt, progress

from pulp.common import pic, tags


# Distributor IDs to not publish by this script
INVALID_DISTRIBUTORS = ('export_distributor',)


# -- public -------------------------------------------------------------------

def run_publish():

    p = prompt.Prompt()

    # Configure the REST interface
    pic.LOG_BODIES = False
    pic.PATH_PREFIX = '/pulp/api/v2/'
    pic.connect()

    # Punch out early if there aren't any repos to publish
    status, repos =  _list_repos()
    if status != 200:
        p.write('No repositories found to publish')
        return os.EX_OK

    # Determine which distributors should be published
    distributors_to_publish = []
    for repo in repos:
        repo_id = repo['id']
        status, repo_distributors = _get_repo_distributors(repo_id)

        valid_distributors = [d for d in repo_distributors if d['id'] not in INVALID_DISTRIBUTORS]
        for distributor in valid_distributors:
            distributor_id, override_config = distributor['id'], distributor['config']
            data = {
                'id' : distributor_id,
                'override_config' : override_config,
            }
            distributors_to_publish.append((repo_id, data))

    # Request a publish for each found distributor
    p.write('Queuing %s publish tasks' % len(distributors_to_publish))
    bar = progress.ProgressBar(p)
    for index, task in enumerate(distributors_to_publish):
        repo_id, data = task
        _publish(repo_id, data)
        bar.render(index, len(distributors_to_publish)-1)
    p.write('')

    # Poll until the publish requests are finished
    p.write('Waiting on publish tasks to complete')
    bar = progress.ProgressBar(p)

    def _get_pending_reports(call_reports):
        return [report for report in call_reports if (report['state'] in ['running', 'waiting'])]

    status, call_reports = _publish_status()
    pending_call_reports = _get_pending_reports(call_reports)
    while len(pending_call_reports) > 0:
        status, call_reports = _publish_status()
        pending_call_reports = _get_pending_reports(call_reports)
        bar.render(len(call_reports) - len(pending_call_reports), len(call_reports))
    p.write('')

    p.write('Completed publishing repositories')

    return os.EX_OK

# -- private ------------------------------------------------------------------

def _list_repos():
    """
    Get all repos within pulp server.
    @return: (status, list of repos)
    """
    return pic.GET('/repositories/')


def _publish(repo_id, data=None):
    """
    Publish the specific repo with associated distributor info
    @param repo_id: repo id to publish
    @param data: dict of post data eg: {'id' : distributor_id, 'override_config' : {}}
    @return: (status, call report representing the current state of they sync)
    """
    return pic.POST('/repositories/%s/actions/publish/' % repo_id, data)


def _publish_status():
    """
    Get all publish tasks.
    @return: (status, list of call reports)
    """
    return pic.GET('/tasks/', tag=tags.action_tag(tags.ACTION_PUBLISH_TYPE))


def _get_repo_distributors(repo_id):
    """
    Get list of distributors associated to a repo
    @param repo_id: repo id to publish
    @return: (status, database representations of all distributors on the repository)
    """
    return pic.GET('/repositories/%s/distributors/' % repo_id)
