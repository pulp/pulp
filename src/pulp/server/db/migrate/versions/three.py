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

from pulp.server.db.model.resource import Errata


_log = logging.getLogger('pulp')

# migration module conventions ------------------------------------------------

version = 3

def _migrate_errata_model():
    collection = Errata.get_collection()
    for erratum in collection.find():
        modified = False
        if 'summary' not in erratum:
            erratum['summary'] = u""
            modified = True
        if 'solution' not in erratum:
            erratum['solution'] = u""
            modified = True
        if modified:
            collection.save(erratum, safe=True)


def migrate():
    _log.info('migration to data model version 3 started')
    _migrate_errata_model()
    _log.info('migration to data model version 3 complete')