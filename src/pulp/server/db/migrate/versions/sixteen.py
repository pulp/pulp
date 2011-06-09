# -*- coding: utf-8 -*-

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

from pulp.server.db.model.persistence import TaskSnapshot


_log = logging.getLogger('pulp')

version = 16

def migrate():
    _log.info('migration to data model version %d started' % version)
    # drop any old serialized tasks
    collection = TaskSnapshot.get_collection()
    collection.remove()
    _log.info('migration to data model version %d complete' % version)
