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
Feed certificates, both CA and client, are stored in the DB under the importer's config.
However, for grinder to use them, they must be saved into the importer's working
directory. This module takes care of creating those files when necessary for all
v2 repositories.

This must be run after both the database has been updated (so the cert contents are
in the importer's config) and the repos filesystem module has been run to create the
working directories.
"""

import os

from pulp.server.upgrade.model import UpgradeStepReport
from pulp.server.upgrade.filesystem import repos


def upgrade(v1_database, v2_database):
    report = UpgradeStepReport()

    # Applies to both yum and iso importers
    repo_importers = v2_database.repo_importers.find()
    for repo_importer in repo_importers:
        repo_working_dir = repos.importer_working_dir(repo_importer['importer_type_id'], repo_importer['repo_id'])

        # CA certificate
        if repo_importer['config']['ssl_ca_cert']:
            filename = os.path.join(repo_working_dir, 'ssl_ca_cert')
            f = open(filename, 'w')
            f.write(repo_importer['config']['ssl_ca_cert'])
            f.close()

        # Client Certificate
        if repo_importer['config']['ssl_client_cert']:
            filename = os.path.join(repo_working_dir, 'ssl_client_cert')
            f = open(filename, 'w')
            f.write(repo_importer['config']['ssl_client_cert'])
            f.close()

    report.succeeded()
    return report
