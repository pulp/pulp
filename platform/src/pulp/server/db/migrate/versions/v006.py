
# -*- coding: utf-8 -*-

# Copyright © 2010-2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

# Migrating all old rpm repositories to have iso_distributor along with yum_distributor

import logging

from pulp.server.db.model.repository import RepoDistributor

YUM_DISTRIBUTOR_TYPE_ID = 'yum_distributor'
ISO_DISTRIBUTOR_TYPE_ID = 'iso_distributor'
ISO_DISTRIBUTOR_CONFIG = {"http" : False, "https" : True, "generate_metadata" : True}

_log = logging.getLogger('pulp')

version = 6

def _migrate_repositories():
    collection = RepoDistributor.get_collection()
    for repo_distributor in collection.find():

        # Check only for rpm repos
        if repo_distributor['distributor_type_id'] == YUM_DISTRIBUTOR_TYPE_ID:

            # Check if an iso_distributor exists for the same repo
            if collection.find_one({'repo_id': repo_distributor['repo_id'], 'distributor_type_id': ISO_DISTRIBUTOR_TYPE_ID}) is None:

                # If not create a new one with default config and same auto_publish flag as corresponding yum distributor
                iso_distributor = RepoDistributor(repo_id = repo_distributor['repo_id'], 
                                                  id = ISO_DISTRIBUTOR_TYPE_ID,
                                                  distributor_type_id = ISO_DISTRIBUTOR_TYPE_ID, 
                                                  config = ISO_DISTRIBUTOR_CONFIG, 
                                                  auto_publish = repo_distributor['auto_publish'])
                collection.save(iso_distributor, safe=True)


def migrate():
    _log.info('migration to data model version %d started' % version)
    _migrate_repositories()
    _log.info('migration to data model version %d complete' % version)



