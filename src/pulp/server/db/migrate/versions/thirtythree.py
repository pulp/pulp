
# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import logging
import os
import pwd
import shutil
from pulp.repo_auth.repo_cert_utils import RepoCertUtils
from pulp.server import config
from pulp.server.db.model import Repo

_LOG = logging.getLogger('pulp')

version = 33

def migrate():
    repo_cert_utils = RepoCertUtils(config.config)
    collection = Repo.get_collection()
    all_repos = list(collection.find())
    apache_pwd = pwd.getpwnam("apache")
    apache_uid = apache_pwd.pw_uid
    apache_gid = apache_pwd.pw_gid
    for r in all_repos:
        try:
            modified = False
            old_repo_cert_dir = None
            for cf in ["feed_cert", "feed_ca", "consumer_ca", "consumer_cert"]:
                if not r.has_key(cf) or not r[cf]:
                    continue
                old_path = r[cf]
                expected_repo_cert_dir = repo_cert_utils._repo_cert_directory(r["id"])
                if old_path.startswith(expected_repo_cert_dir):
                    continue
                # We have existing cert files which do not match the configuration
                # Move these to the new location
                updated_path = os.path.join(expected_repo_cert_dir, os.path.basename(old_path))
                _LOG.info("Moving %s to %s" % (old_path, updated_path))
                if not os.path.exists(expected_repo_cert_dir):
                    os.makedirs(expected_repo_cert_dir)
                    os.chown(expected_repo_cert_dir, apache_uid, apache_gid)
                shutil.copy(old_path, updated_path)
                os.chown(updated_path, apache_uid, apache_gid)
                r[cf] = updated_path
                modified = True
                old_repo_cert_dir = os.path.dirname(old_path)
            if old_repo_cert_dir is not None:
                shutil.rmtree(old_repo_cert_dir)
            if modified:
                collection.save(r, safe=True)
        except Exception, e:
            _LOG.critical(e)
            raise e
    return True


