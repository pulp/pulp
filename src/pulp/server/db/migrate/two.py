# -*- coding: utf-8 -*-

# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import logging
import traceback
import sys

from pulp.server.db import version
from pulp.server.db.migrate import utils

from pulp.server.api import (repo, user)

_log = logging.getLogger('pulp')

repoApi = repo.RepoApi()
userApi = user.UserApi()
repo_db = repoApi._getcollection()
user_db = userApi._getcollection()

def get_repo_package_count():
    repoApi = repo.RepoApi()
    return lambda m: repoApi.package_count(m[id])

def migrate():
    _log.info('migration to data model version 2 starting')

    try:
        # Repo model migration
        utils.add_field_with_calculated_value(repo_db, "package_count", get_repo_package_count)
        utils.add_field_with_default_value(repo_db, "distributionid", [])

        # User model migration
        utils.add_field_with_default_value(user_db, "roles", [])
        utils.change_field_type_with_default_value(user_db, "roles", list, [])


    except Exception, e:
        _log.critical(str(e))
        _log.critical(''.join(traceback.format_exception(*sys.exc_info())))
        _log.critical('migration to data model version 2 failed')
        raise

    _log.info('migration to data model version 2 complete')


def set_version():
    version.set_version(2)
