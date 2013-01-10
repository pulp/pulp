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

"""
Handles the upgrade for v1 file repositories. The yum repositories are handled
in a different module.
"""

from pulp.server.upgrade.model import UpgradeStepReport


# The CLI for adding these sorts of repos doesn't exist when this is written,
# so this is effectively defining what it will have to look like
ISO_IMPORTER_TYPE_ID = 'iso_importer'
ISO_IMPORTER_ID = ISO_IMPORTER_TYPE_ID
ISO_DISTRIBUTOR_TYPE_ID = 'iso_distributor'
ISO_DISTRIBUTOR_ID = ISO_DISTRIBUTOR_TYPE_ID

# Value for the flag in v1 that distinguishes the type of repo
V1_ISO_REPO = 'file'


def upgrade(v1_database, v2_database):

    # This is written after the yum repository upgrade and will use similar
    # patterns. Rather than rewrite all of the comments here, please check
    # that file for more information if anything looks confusing.

    report = UpgradeStepReport()

    return report
