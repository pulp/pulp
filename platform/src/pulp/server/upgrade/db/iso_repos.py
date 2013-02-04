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
Handles the upgrade for v1 file repositories. The yum repositories are handled
in a different module.
"""

from ConfigParser import SafeConfigParser

from pulp.server.compat import ObjectId
from pulp.server.upgrade.model import UpgradeStepReport


# The CLI for adding these sorts of repos doesn't exist when this is written,
# so this is effectively defining what it will have to look like
ISO_IMPORTER_TYPE_ID = 'iso_importer'
ISO_IMPORTER_ID = ISO_IMPORTER_TYPE_ID
ISO_DISTRIBUTOR_TYPE_ID = 'iso_distributor'
ISO_DISTRIBUTOR_ID = ISO_DISTRIBUTOR_TYPE_ID

# Notes added to repos to easily differentiate them; copied from the RPM support
REPO_NOTE_KEY = '_repo-type' # needs to be standard across extensions
REPO_NOTE_ISO = 'iso-repo'

# Value for the flag in v1 that distinguishes the type of repo
V1_ISO_REPO = 'file'

# Can be set by unit tests running against a database export (without a full
# installation) to prevent the script from blowing up when it can't find the
# local files to read.
SKIP_SERVER_CONF = False

# Location to load when looking for static server.conf configuration, should
# only be changed by unit tests not running on a full installation.
# See note in yum_repos about a similar constant.
V1_SERVER_CONF = '/etc/pulp/pulp.conf'


def upgrade(v1_database, v2_database):

    # This is written after the yum repository upgrade and will use similar
    # patterns. Rather than rewrite all of the comments here, please check
    # that file for more information if anything looks confusing.

    report = UpgradeStepReport()

    repo_success = _repos(v1_database, v2_database)
    importer_success = _repo_importers(v1_database, v2_database, report)
    distributor_success = _repo_distributors(v1_database, v2_database, report)

    report.success = (repo_success and importer_success and distributor_success)
    return report


def _repos(v1_database, v2_database):
    v1_coll = v1_database.repos
    v2_coll = v2_database.repos

    # Idempotency: By repo_id
    v2_repo_ids = [x['id'] for x in v2_coll.find({}, {'id' : 1})]
    spec = {
        '$and' : [
            {'id' : {'$nin' : v2_repo_ids}},
            {'content_types' : V1_ISO_REPO},
        ]
    }
    missing_v1_repos = v1_coll.find(spec)

    new_repos = []
    for v1_repo in missing_v1_repos:
        id = ObjectId()

        # Identifying tag for the CLI
        v2_notes = v1_repo.get('notes', {})
        v2_notes[REPO_NOTE_KEY] = REPO_NOTE_ISO

        v2_repo = {
            '_id' : id, # technically not needed but added for clarity
            'id' : v1_repo['id'],
            'display_name' : v1_repo['name'],
            'description' : None,
            'notes' : v2_notes,
            'scratchpad' : {},
            'content_unit_count' : 0
        }
        new_repos.append(v2_repo)

    if new_repos:
        v2_coll.insert(new_repos, safe=True)

    return True


def _repo_importers(v1_database, v2_database, report):
    v1_coll = v1_database.repos
    v2_repo_coll = v2_database.repos
    v2_imp_coll = v2_database.repo_importers

    # Idempotency: There is a single importer per repo, so we can simply check
    # for an importer with the given repo ID
    v2_importer_repo_ids = [x['repo_id'] for x in v2_imp_coll.find({}, {'repo_id' : 1})]
    spec = {
        '$and' : [
            {'id' : {'$nin' : v2_importer_repo_ids}},
            {'content_types' : V1_ISO_REPO},
        ]
    }
    missing_v1_repos = v1_coll.find(spec)

    new_importers = []
    for v1_repo in missing_v1_repos:

        # Sanity check that the repository was added to v2. This should never
        # happen, but we should account for it anyway.
        v2_repo = v2_repo_coll.find_one({'id' : v1_repo['id']})
        if v2_repo is None:
            report.error('Repository [%s] not found in the v2 database; '
                         'importer addition being canceled' % v1_repo['id'])
            return False

        new_importer = {
            '_id' : ObjectId(),
            'id' : ISO_IMPORTER_ID,
            'repo_id' : v1_repo['id'],
            'importer_type_id' : ISO_IMPORTER_TYPE_ID,
            'scratchpad' : None,
            'last_sync' : v1_repo['last_sync'],
            'scheduled_syncs' : [],
        }

        # The configuration intentionally omits the importer configuration
        # values: num_threads, num_old_packages, remove_old, verify_checksum,
        #         verify_size, max_speed
        # Being omitted will cause the yum importer to use the default, which
        # is the desired behavior of the upgrade.

        config = {
            'feed_url' : None, # set below
            'ssl_ca_cert' : v1_repo['feed_ca'],
            'ssl_client_cert' : v1_repo['feed_cert'],
        }

        if v1_repo['source']: # will be None for a feedless repo
            config['feed_url'] = v1_repo['source']['url']

        # Load values from the static server.conf file
        if not SKIP_SERVER_CONF:
            parser = SafeConfigParser()
            parser.read(V1_SERVER_CONF)

            for o in ('proxy_url', 'proxy_port', 'proxy_user', 'proxy_pass'):
                if parser.has_option('yum', o):
                    config[o] = parser.get('yum', o)

        new_importer['config'] = config
        new_importers.append(new_importer)

    if new_importers:
        v2_imp_coll.insert(new_importers, safe=True)

    return True


def _repo_distributors(v1_database, v2_database, report):
    v1_coll = v1_database.repos
    v2_repo_coll = v2_database.repos
    v2_dist_coll = v2_database.repo_distributors

    # Idempotency: Only one distributor is added per repo, so check for that
    v2_distributor_repo_ids = [x['repo_id'] for x in v2_dist_coll.find({}, {'repo_id' : 1})]
    spec = {
        '$and' : [
            {'id' : {'$nin' : v2_distributor_repo_ids}},
            {'content_types' : V1_ISO_REPO},
        ]
    }
    missing_v1_repos = v1_coll.find(spec)

    new_distributors = []
    for v1_repo in missing_v1_repos:

        # Sanity check that the repository was added to v2. This should never
        # happen, but we should account for it anyway.
        v2_repo = v2_repo_coll.find_one({'id' : v1_repo['id']})
        if v2_repo is None:
            report.error('Repository [%s] not found in the v2 database; '
                         'distributor addition being canceled' % v1_repo['id'])
            return False

        new_distributor = {
            '_id' : ObjectId(),
            'id' : ISO_DISTRIBUTOR_ID,
            'repo_id' : v1_repo['id'],
            'distributor_type_id' : ISO_DISTRIBUTOR_TYPE_ID,
            'auto_publish' : True,
            'scratchpad' : None,
            'last_publish' : v1_repo['last_sync'], # in v1 sync and publish are the same, so close enough
            'scheduled_publishes' : [], # scheduling a publish doesn't exist in v1, leave this empty
        }

        config = {
            'relative_url' : v1_repo['relative_path'],
            'http' : False,
            'https' : True,
        }

        new_distributor['config'] = config
        new_distributors.append(new_distributor)

    if new_distributors:
        v2_dist_coll.insert(new_distributors, safe=True)

    return True

