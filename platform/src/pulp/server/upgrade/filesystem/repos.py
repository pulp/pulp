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

"""
Initializes the working directories for all v2 repositories. This script will
also create the directories beneath each repository working directory for the
yum importer and distributor.

The permissions script will take care of moving the permissions of these
directories from root to apache.
"""

import os


# Location in which all working directories are found.
from pulp.server.upgrade.model import UpgradeStepReport

WORKING_DIR_ROOT = '/var/lib/pulp/working/repos'


def upgrade(v1_database, v2_database):
    report = UpgradeStepReport()

    # Idempotency: Each of the *_working_dir calls below will check for the
    # directory's existence first, so there's nothing special to do here.

    # Importers
    all_importers = v2_database.repo_importers.find({})
    for i in all_importers:
        repo_id = i['repo_id']
        importer_type_id = i['importer_type_id']
        importer_working_dir(importer_type_id, repo_id)

    # Distributors
    all_distributors = v2_database.repo_distributors.find({})
    for d in all_distributors:
        repo_id = d['repo_id']
        distributor_type_id = d['distributor_type_id']
        distributor_working_dir(distributor_type_id, repo_id)

    report.succeeded()
    return report


def repository_working_dir(repo_id, mkdir=True):
    working_dir = os.path.join(WORKING_DIR_ROOT, repo_id)

    if mkdir and not os.path.exists(working_dir):
        os.makedirs(working_dir)

    return working_dir


def importer_working_dir(importer_type_id, repo_id, mkdir=True):
    repo_working_dir = repository_working_dir(repo_id, mkdir=mkdir)
    working_dir = os.path.join(repo_working_dir, 'importers', importer_type_id)

    if mkdir and not os.path.exists(working_dir):
        os.makedirs(working_dir)

    return working_dir


def distributor_working_dir(distributor_type_id, repo_id, mkdir=True):
    repo_working_dir = repository_working_dir(repo_id, mkdir=mkdir)
    working_dir = os.path.join(repo_working_dir, 'distributors', distributor_type_id)

    if mkdir and not os.path.exists(working_dir):
        os.makedirs(working_dir)

    return working_dir
