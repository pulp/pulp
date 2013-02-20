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
Handles the upgrade for v1 yum repositories. The file repositories are handled
in a different module.
"""

import os
from ConfigParser import SafeConfigParser

from pulp.server.compat import ObjectId
from pulp.server.upgrade.model import UpgradeStepReport


# The same values that the client sets when creating an RPM repository
YUM_IMPORTER_TYPE_ID = 'yum_importer'
YUM_IMPORTER_ID = YUM_IMPORTER_TYPE_ID
YUM_DISTRIBUTOR_TYPE_ID = 'yum_distributor'
YUM_DISTRIBUTOR_ID = YUM_DISTRIBUTOR_TYPE_ID

# Notes added to repos to easily differentiate them; copied from the RPM support
REPO_NOTE_KEY = '_repo-type' # needs to be standard across extensions
REPO_NOTE_RPM = 'rpm-repo'

# Value for the flag in v1 that distinguishes the type of repo
V1_YUM_REPO = 'yum'

# Can be set by unit tests running against a database export (without a full
# installation) to prevent the script from blowing up when it can't find the
# local files to read.
SKIP_SERVER_CONF = False
SKIP_GPG_KEYS = False

# Location to load when looking for static server.conf configuration, should
# only be changed by unit tests not running on a full installation.
# This file is deleted in the normal v1 upgrade. The functionality remains in
# this script (it won't break if it's not present) in the event Katello wants
# to add their own backup/restore step to retain this file.
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

    report.success = (repo_success and importer_success and
                      distributor_success)
    return report


def _repos(v1_database, v2_database):
    v1_coll = v1_database.repos
    v2_coll = v2_database.repos

    # Idempotency: Nice and easy, repo_id is the test
    v2_repo_ids = [x['id'] for x in v2_coll.find({}, {'id' : 1})]
    spec = {
        '$and' : [
            {'id' : {'$nin' : v2_repo_ids}},
            {'content_types' : V1_YUM_REPO},
        ]
    }
    missing_v1_repos = v1_coll.find(spec)

    new_repos = []
    for v1_repo in missing_v1_repos:
        id = ObjectId()

        # Identifying tag for the CLI
        v2_notes = v1_repo.get('notes', {})
        v2_notes[REPO_NOTE_KEY] = REPO_NOTE_RPM

        v2_repo = {
            '_id' : id, # technically not needed but added for clarity
            'id' : v1_repo['id'],
            'display_name' : v1_repo.get('name', v1_repo['id']),
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
            {'content_types' : V1_YUM_REPO},
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
            'id' : YUM_IMPORTER_ID,
            'repo_id' : v1_repo['id'],
            'importer_type_id' : YUM_IMPORTER_TYPE_ID,
            'scratchpad' : None,
            'last_sync' : v1_repo['last_sync'],
            'scheduled_syncs' : [],
        }

        # The configuration intentionally omits the importer configuration
        # values: num_threads, num_old_packages, remove_old, verify_checksum,
        #         verify_size, max_speed
        # Being omitted will cause the yum importer to use the default, which
        # is the desired behavior of the upgrade.

        # All are set below. To keep consistent with a fresh install, the fields aren't
        # defaulted to None but rather omitted entirely.
        config = {}

        if v1_repo['source']:  # will be None for a feedless repo
            config['feed_url'] = v1_repo['source']['url']

        # Load the certificate content into the database. It needs to be written to the
        # working directory as well, but that will be done in the filesystem scripts.
        if v1_repo['feed_ca']:
            if not os.path.exists(v1_repo['feed_ca']):
                continue

            f = open(v1_repo['feed_ca'], 'r')
            cert = f.read()
            f.close()

            config['ssl_ca_cert'] = cert

        if v1_repo['feed_cert']:
            if not os.path.exists(v1_repo['feed_cert']):
                continue

            f = open(v1_repo['feed_cert'], 'r')
            cert = f.read()
            f.close()

            config['ssl_client_cert'] = cert

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

    # Only the yum distributor is added in this process. The export distributor
    # will be added to any repositories that do not have it as part of the
    # normal DB migration process.

    # Idempotency: Only one distributor is added per repo, so check for that
    v2_distributor_repo_ids = [x['repo_id'] for x in v2_dist_coll.find({}, {'repo_id' : 1})]
    spec = {
        '$and' : [
            {'id' : {'$nin' : v2_distributor_repo_ids}},
            {'content_types' : V1_YUM_REPO},
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
            'id' : YUM_DISTRIBUTOR_ID,
            'repo_id' : v1_repo['id'],
            'distributor_type_id' : YUM_DISTRIBUTOR_TYPE_ID,
            'auto_publish' : True,
            'scratchpad' : None,
            'last_publish' : v1_repo['last_sync'], # in v1 sync and publish are the same, so close enough
            'scheduled_publishes' : [],  # likely don't need to revisit, the sync/auto-publish will take care
        }

        config = {
            'relative_url' : v1_repo['relative_path'],
            'http' : False,
            'https' : True,
        }

        # Load values from the static server.conf file
        if not SKIP_SERVER_CONF:
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
        repo_key_dir = os.path.join(GPG_KEY_ROOT, v1_repo['relative_path'])
        if os.path.exists(repo_key_dir) and not SKIP_GPG_KEYS:
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

    if new_distributors:
        v2_dist_coll.insert(new_distributors, safe=True)

    return True

