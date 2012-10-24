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

from ConfigParser import SafeConfigParser

from pymongo.objectid import ObjectId

from pulp.server.upgrade.model import UpgradeStepReport


# The same ID that the client sets when creating an RPM repository
YUM_IMPORTER_ID = 'yum_importer'

# Can be set by unit tests running against a database export (without a full
# installation) to prevent the script from blowing up when it can't find the
# local files to read.
SKIP_LOCAL_FILES = False

# Location to load when looking for static server.conf configuration, should
# only be changed by unit tests not running on a full installation.
# Note: need to figure out what happens to this file when doing an upgrade
V1_SERVER_CONF = '/etc/pulp/pulp.conf'


def upgrade(v1_database, v2_database):

    # It's very important that each repository have its associated importer
    # and distributor created. Each will be done in its own pass, allowing us
    # to use idempotency checks instead of attempting to ensure a transaction
    # across the three creates. The idea is that if one of these fails to
    # get created on a run of the upgrade, the next time it is run it will
    # be created, assuming the second run will have fixed any errors that
    # arose due to data in the db already (which shouldn't happen assuming we
    # QE this properly) or because the user aborted the upgrade.

    report = UpgradeStepReport()

    repo_success = _repos(v1_database, v2_database)
    importer_success = _repo_importers(v1_database, v2_database, report)
    distributor_success = _repo_distributors(v1_database, v2_database, report)

    report.success = repo_success and importer_success and distributor_success
    return report


def _repos(v1_database, v2_database):
    v1_coll = v1_database.repos
    v2_coll = v2_database.repos

    # Idempotency: Nice and easy, repo_id is the test
    v2_repo_ids = [x['id'] for x in v2_coll.find({}, {'id' : 1})]
    missing_v1_repos = v1_coll.find({'id' : {'$nin' : v2_repo_ids}})

    new_repos = []
    for v1_repo in missing_v1_repos:
        id = ObjectId()
        v2_repo = {
            '_id' : id, # technically not needed but added for clarity
            'id' : v1_repo['id'],
            'display_name' : v1_repo['name'],
            'description' : None,
            'notes' : v1_repo['notes'],
            'scratchpad' : {'checksum_type' : v1_repo['checksum_type']},
            'content_unit_count' : 0
        }
        new_repos.append(v2_repo)

    v2_coll.insert(new_repos)


def _repo_importers(v1_database, v2_database, report):
    v1_coll = v1_database.repos
    v2_coll = v2_database.repo_importers

    # Idempotency: There is a single importer per repo, so we can simply check
    # for an importer with the given repo ID
    v2_importer_repo_ids = [x['repo_id'] for x in v2_coll.find({}, {'repo_id' : 1})]
    missing_v1_repos = v1_coll.find({'id' : {'$nin' : v2_importer_repo_ids}})

    for v1_repo in missing_v1_repos:
        new_id = ObjectId()
        new_importer = {
            '_id' : new_id,
            'id' : new_id,
            'repo_id' : v1_repo['id'],
            'importer_type_id' : YUM_IMPORTER_ID,
            'scratchpad' : None,
            'last_sync' : v1_repo['last_sync'],
            'scheduled_syncs' : [], # likely need to revisit
        }

        # The configuration intentionally omits the importer configuration
        # values: num_threads, num_old_packages, remove_old, verify_checksum,
        #         verify_size, max_speed
        # Being omitted will cause the yum importer to use the default, which
        # is the desired behavior of the upgrade.

        config = {
            'feed' : None, # set below
            'skip' : None,
            'ssl_ca_cert' : v1_repo['feed_ca'],
            'ssl_client_cert' : v1_repo['feed_cert'],
        }

        if v1_repo['source']: # will be None for a feedless repo
            config['feed'] = v1_repo['source']['url']

        # Load values from the static server.conf file
        if not SKIP_LOCAL_FILES:
            parser = SafeConfigParser()
            parser.read(V1_SERVER_CONF)

            for o in ('proxy_url', 'proxy_port', 'proxy_user', 'proxy_pass'):
                if parser.has_option('yum', o):
                    config[o] = parser.get('yum', o)


def _repo_distributors(v1_database, v2_database, report):
    pass
