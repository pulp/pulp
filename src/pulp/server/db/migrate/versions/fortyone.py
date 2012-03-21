# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
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

from pulp.server.db.model.resource import Errata, Package, Repo

_log = logging.getLogger('pulp')

version = 41

def _drop_errata_index():
    errata_coln = Errata.get_collection()
    for idx, idx_info in errata_coln.index_information().items():
        for key in idx_info["key"]:
            if key[0] == "description":
                _log.info("Dropping index %s from errata collection." % idx)
                errata_coln.drop_index(idx)
                return

def _drop_package_index():
    pkg_coln = Package.get_collection()
    for idx, idx_info in pkg_coln.index_information().items():
        for key in idx_info["key"]:
            if key[0] == "description":
                _log.info("Dropping index %s from package collection." % idx)
                pkg_coln.drop_index(idx)
                return

def _drop_repo_index():
    repo_coln = Repo.get_collection()
    for idx, idx_info in repo_coln.index_information().items():
       	for key in idx_info["key"]:
            if key[0] in ("packagegroups", "packagegroupcategories"):
               	_log.info("Dropping index %s from package collection." % idx)
               	repo_coln.drop_index(idx)

def _add_repo_index():
    repo_coln = Repo.get_collection()
    _log.info("Adding index on errata to Repo collection.")
    repo_coln.ensure_index("errata")

def migrate():
    _log.info('migration to data model version %d started' % version)
    _drop_errata_index()
    _drop_package_index()
    _drop_repo_index()
    _add_repo_index()
    _log.info('migration to data model version %d complete' % version)
