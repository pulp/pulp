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

from gettext import gettext as _
import os
import shutil

from pulp.server.upgrade.model import UpgradeStepReport


CLEAN_UP_DIRS = (
    '/var/lib/pulp/packages',
    '/var/lib/pulp/files',
    '/var/lib/pulp/cache',
)


def upgrade(v1_database, v2_database):
    """
    Deletes the v1 directories that are no longer used. Needless to say, this
    upgrade should be done last in the series of filesystem upgrades.

    Databases are unused but necessary for the API into these upgrade scripts.
    """

    report = UpgradeStepReport()

    for dir in CLEAN_UP_DIRS:
        if not os.path.exists(dir):
            continue

        try:
            shutil.rmtree(dir)
        except Exception, e:
            report.warning(_('Unable to delete directory: %(d)s') % dir)

    report.succeeded() # don't fail the entire upgrade if these can't be cleaned up
    return report
