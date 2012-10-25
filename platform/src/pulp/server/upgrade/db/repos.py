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
import os

from pymongo.objectid import ObjectId

from pulp.server.upgrade.model import UpgradeStepReport


# The same values that the client sets when creating an RPM repository
YUM_IMPORTER_ID = 'yum_importer'
YUM_IMPORTER_TYPE_ID = YUM_IMPORTER_ID
YUM_DISTRIBUTOR_ID = 'yum_distributor'
YUM_DISTRIBUTOR_TYPE_ID = YUM_DISTRIBUTOR_ID

# Can be set by unit tests running against a database export (without a full
# installation) to prevent the script from blowing up when it can't find the
# local files to read.
SKIP_LOCAL_FILES = False

# Location to load when looking for static server.conf configuration, should
# only be changed by unit tests not running on a full installation.
# Note: need to figure out what happens to this file when doing an upgrade
V1_SERVER_CONF = '/etc/pulp/pulp.conf'

# Root directory in which GPG keys are located
GPG_KEY_ROOT = '/var/www/pub/gpg/'


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
    group_success = _repo_groups(v1_database, v2_database, report)

    report.success = (repo_success and importer_success and
                      distributor_success and group_success)
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
            'scratchpad' : {},
            'content_unit_count' : 0
        }
        new_repos.append(v2_repo)

    v2_coll.insert(new_repos, safe=True)

    return True


def _repo_importers(v1_database, v2_database, report):
    v1_coll = v1_database.repos
    v2_repo_coll = v2_database.repos
    v2_imp_coll = v2_database.repo_importers

    # Idempotency: There is a single importer per repo, so we can simply check
    # for an importer with the given repo ID
    v2_importer_repo_ids = [x['repo_id'] for x in v2_imp_coll.find({}, {'repo_id' : 1})]
    missing_v1_repos = v1_coll.find({'id' : {'$nin' : v2_importer_repo_ids}})

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
            'id' : YUM_IMPORTER_ID,
            'repo_id' : v1_repo['id'],
            'importer_type_id' : YUM_IMPORTER_TYPE_ID,
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

        new_importer['config'] = config
        new_importers.append(new_importer)

    if new_importers:
        v2_imp_coll.insert(new_importers, safe=True)

    return True


def _repo_distributors(v1_database, v2_database, report):
    v1_coll = v1_database.repos
    v2_repo_coll = v2_database.repos
    v2_dist_coll = v2_database.repo_distributors

    # Only the yum distributor is added in this process. The ISO distributor
    # will be added to any repositories that do not have it as part of the
    # normal DB migration process.

    # Idempotency: There is a single importer per repo, so we can simply check
    # for an importer with the given repo ID
    v2_distributor_repo_ids = [x['repo_id'] for x in v2_dist_coll.find({}, {'repo_id' : 1})]
    missing_v1_repos = v1_coll.find({'id' : {'$nin' : v2_distributor_repo_ids}})

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
            'id' : YUM_DISTRIBUTOR_ID,
            'repo_id' : v1_repo['id'],
            'distributor_type_id' : YUM_DISTRIBUTOR_TYPE_ID,
            'auto_publish' : True,
            'scratchpad' : None,
            'last_publish' : v1_repo['last_sync'], # in v1 sync and publish are the same, so close enough
            'scheduled_publishes' : [], # likely don't need to revisit, the sync and auto publish will take care
        }

        config = {
            'relative_url' : v1_repo['relative_path'],
            'http' : False,
            'https' : True,
        }

        # Load values from the static server.conf file
        if not SKIP_LOCAL_FILES:
            parser = SafeConfigParser()
            parser.read(V1_SERVER_CONF)

            if parser.has_option('security', 'ssl_ca_certificate'):
                # Read in the contents of the certificate and store in the
                # configuration in the DB.
                ca_filename = parser.get('security', 'ssl_ca_certificate')
                try:
                    # Not bothering with a existence check, let any problems
                    # trigger the warning in the except
                    f = open(ca_filename, 'r')
                    ca_cert_contents = f.read()
                    f.close()
                    config['https_ca'] = ca_cert_contents
                except:
                    report.warning('Could not read SSL CA certificate at [%s] for '
                                   'repository [%s]' % (ca_filename, v1_repo['id']))

        # Load the GPG keys from disk if present
        if not SKIP_LOCAL_FILES:
            repo_key_dir = os.path.join(GPG_KEY_ROOT, v1_repo['relative_path'])
            key_filenames = os.listdir(repo_key_dir)
            if len(key_filenames) > 0:
                filename = os.path.join(repo_key_dir, key_filenames[0])

                try:
                    f = open(filename, 'r')
                    key_contents = f.read()
                    f.close()
                    config['gpgkey'] = key_contents
                except:
                    report.warning('Could not read GPG key at [%s] for '
                                   'repository [%s]' % (filename, v1_repo['id']))

        new_distributor['config'] = config
        new_distributors.append(new_distributor)

    v2_dist_coll.insert(new_distributors, safe=True)

    return True


def _repo_groups(v1_database, v2_database, report):
    v1_coll = v1_database.repos
    v2_coll = v2_database.repo_groups

    # Idempotency: Two-fold. All group IDs will be collected and groups created
    # from those IDs, using the ID to determine if it already exists. The second
    # is the addition of repo IDs to the group, which will be handled by mongo.

    # I should probably use a map reduce here, but frankly this is simpler and
    # I'm not terribly worried about either the mongo performance or memory
    # consumption from the approach below.
    repo_and_group_ids = [(x['id'], x['groupid']) for x in v1_coll.find({}, {'id' : 1, 'groupid' : 1})]
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
