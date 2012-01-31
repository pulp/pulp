# -*- coding: utf-8 -*-

# Copyright © 2010-2011 Red Hat, Inc.
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

from pulp.server.db.model.resource import Errata


_log = logging.getLogger('pulp')

# migration module conventions ------------------------------------------------

version = 17

# NOTE: This db change has moved to version 22 to account for pushcount fix
def migrate():
    _log.info('migration to data model version 17 started')
    _log.info('migration to data model version 17 complete')
