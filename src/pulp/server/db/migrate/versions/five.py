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

from pulp.server.db.model.cds import CDS


_log = logging.getLogger('pulp')

# migration module conventions ------------------------------------------------

version = 5

def _migrate_cds_model():
    collection = CDS.get_collection()
    for cds in collection.find():
        if 'secret' not in cds:
            repo['secret'] = None
            collection.save(cds, safe=True)


def migrate():
    _log.info('migration to data model version 5 started')
    _migrate_cds_model()
    _log.info('migration to data model version 5 complete')