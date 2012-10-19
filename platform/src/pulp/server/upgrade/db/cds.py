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

from pulp.server.upgrade.model import UpgradeStepReport


def upgrade(v1_database, v2_database):

    # At the time of this upgrade, we don't know what CDS implementation will
    # look like in v2. There's a really good chance that it'll look so
    # drastically different on the CDS side that it won't be migratable anyway,
    # so we're not copying anything CDS-related from the v1 database into
    # the v2.
    #
    # tl;dr - Intentionally a no-op

    report = UpgradeStepReport()
    report.succeeded()
    return report
