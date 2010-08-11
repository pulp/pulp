#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
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


_connection = None
_database = None

_log = logging.getLogger(__name__)

# connection api --------------------------------------------------------------

def _initialize():
    """
    Initialize the connection pool and top-level database for pulp.
    """
    global _connection, _database
    try:
        _connection = pymongo.Connection()
        _database = _connection._database
        _database.add_son_manipulator(NamespaceInjector())
        _database.add_son_manipulator(AutoReference(_database))
    except Exception:
        _log.critical('Database initialization failed')
        _connection = None
        _database = None
        raise
    
    
def get_object_db(name, unique_indexes=[], other_indexes=[], order=pymongo.DESCENDING):
    """
    Get an object database (read MongoDB Document Collection) for the given name.
    Build in indexes in the given order.
    @type name: basestring instance or derived instance
    @param name: name of the object database to get
    @type unique_indexes: iterable of str's
    @param unique_indexes: unique indexes of the database
    @type other_indexes: iterable of str's
    @param other_indexes: non-unique indexes of the database
    @type order: either pymongo.ASCENDING or pymongo.DESCENDING
    @param order: order of the database indexes
    """
    if _database is None:
        raise RuntimeError('Database is not initialized')
    objdb = getattr(_database, name)
    for index in unique_indexes:
        _log.debug('Object DB %s: adding unique index: %s' % (objdb.name, index))
        objdb.ensure_index([(index, order)], unique=True, background=True)
    for index in other_indexes:
        _log.debug('Object DB %s: adding non-unique index: %s' % (objdb.name, index))
        objdb.ensure_index([(index, order)], unique=False, background=True)
    return objdb

# initialize on import --------------------------------------------------------

_initialize()