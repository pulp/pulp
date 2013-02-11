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

from pulp.server.upgrade.model import UpgradeStepReport


DIRS = (
    '/var/lib/pulp/content',
    '/var/lib/pulp/working',
)


def upgrade(v1_database, v2_database):
    """
    Corrects the permissions of the v2 content filesystem.

    Databases are unused but necessary for the upgrade API.
    """
    report = UpgradeStepReport()

    for dir in DIRS:

        success = False
        try:
            exit_code = os.system('chown -R apache:apache %s' % dir)
            success = (exit_code == 0)
        except:
            pass

        if not success:
            report.error(_('Could not correct permissions for directory: %(d)s') % {'d' : dir})
            report.failed()

    if len(report.errors) == 0:
        report.succeeded()

    return report
