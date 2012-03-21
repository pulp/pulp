
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
from pulp.server.db.model import Package, Errata, Repo

_LOG = logging.getLogger('pulp')

version = 35

def _drop_errata_index():
    errata_coln = Errata.get_collection()
    for idx, idx_info in errata_coln.index_information().items():
        for key in idx_info["key"]:
            if key[0] == "description":
                _LOG.info("Dropping index %s from errata collection." % idx)
                errata_coln.drop_index(idx)
                return

def _drop_package_index():
    pkg_coln = Package.get_collection()
    for idx, idx_info in pkg_coln.index_information().items():
        for key in idx_info["key"]:
            if key[0] == "description":
                _LOG.info("Dropping index %s from package collection." % idx)
                pkg_coln.drop_index(idx)
                return

def _drop_repo_index():
    repo_coln = Repo.get_collection()
    for idx, idx_info in repo_coln.index_information().items():
        for key in idx_info["key"]:
            if key[0] in ("packagegroups", "packagegroupcategories"):
                _LOG.info("Dropping index %s from package collection." % idx)
                repo_coln.drop_index(idx)

def _migrate_packages():
    pkg_collection = Package.get_collection()
    repo_collection = Repo.get_collection()
    repo_collection.ensure_index("errata")
    all_packages = list(pkg_collection.find())
    _LOG.info('migrating %s packages' % len(all_packages))
    for pkg in all_packages:
        try:
            modified = False
            found = repo_collection.find({"packages":pkg['id']}, fields=["id"])
            repos = [r["id"] for r in found]
            if not pkg.has_key('repoids') or not pkg['repoids']:
                pkg['repoids'] = repos
                modified =True
            if modified:
                pkg_collection.save(pkg, safe=True)
        except Exception, e:
            _LOG.critical(e)
            return False
    return True

def _migrate_errata():
    collection = Errata.get_collection()
    all_errata = list(collection.find())
    _LOG.info('migrating %s errata' % len(all_errata))
    for e in all_errata:
        try:
            modified = False
            repos = find_errata_repos(e['id'])
            if not e.has_key('repoids') or not e['repoids']:
                e['repoids'] = repos
                modified =True
            if modified:
                collection.save(e, safe=True)
        except Exception, e:
            _LOG.critical(e)
            return False
    return True

def find_errata_repos(errata_id):
    """
    Return repos that contain passed in errata_id
    """
    repos = []
    e_types = ["enhancement", "security", "bugfix"]
    collection = Repo.get_collection()

    for e_type in e_types:
        key = "errata.%s" % (e_type)
        for r in collection.find({key:errata_id}):
            if r["id"] not in repos:
                repos += r
    return repos

def migrate():
    _drop_errata_index()
    _drop_package_index()
    _drop_repo_index()
    _LOG.info('migrating packages to include repoids field')
    _migrate_packages()
    _LOG.info('migrating errata to include repoids field')
    _migrate_errata()
