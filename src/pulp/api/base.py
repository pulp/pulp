#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import logging
import pymongo
from pymongo.son_manipulator import AutoReference, NamespaceInjector

log = logging.getLogger('pulp.api.base')

class BaseApi(object):

    def __init__(self):
        # Mongo DB
        self.connection = pymongo.Connection()
        self.db = self.connection._database
        # Inject the collection's namespace into each object
        self.db.add_son_manipulator(NamespaceInjector())
        # Provides auto-referencing/auto-dereferencing ability
        self.db.add_son_manipulator(AutoReference(self.db))
        self.objectdb = self._getcollection()

        if self.objectdb:
            # Indexes
            for index in self._get_unique_indexes():
                log.info("'%s' ensure_index('%s', unique=True)" % (self._getcollection().name, index))
                self.objectdb.ensure_index([(index, pymongo.DESCENDING)], unique=True, 
                                   background=True)
            for index in self._get_indexes():
                log.info("'%s' ensure_index('%s')" % (self._getcollection().name, index))
                self.objectdb.ensure_index([(index, pymongo.DESCENDING)], background=True)
   
    def _get_unique_indexes(self):
        return ["id"]

    def _get_indexes(self):
        return []

    def clean(self):
        """
        Delete all the Objects in the database.  WARNING: Destructive
        """
        self.objectdb.remove()

    def update(self, object):
        """
        Write the object document to the database
        """
        self.objectdb.save(object, safe=True)

    def delete(self, id):
        """
        Delete a single stored Object
        """
        self.objectdb.remove({'id': id})
        
    def _getcollection(self):
        return
