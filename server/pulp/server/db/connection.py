# -*- coding: utf-8 -*-
#
# Copyright © 2010-2013 Red Hat, Inc.
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
import time
from gettext import gettext as _

import pymongo
from pymongo.collection import Collection
from pymongo.errors import AutoReconnect
from pymongo.son_manipulator import NamespaceInjector

from pulp.server import config
from pulp.server.compat import wraps
from pulp.server.exceptions import PulpException

# globals ----------------------------------------------------------------------

_CONNECTION = None
_DATABASE = None

_LOG = logging.getLogger(__name__)
_DEFAULT_MAX_POOL_SIZE = 10

# -- connection api ------------------------------------------------------------

def initialize(name=None, seeds=None, max_pool_size=None):
    """
    Initialize the connection pool and top-level database for pulp.
    """
    global _CONNECTION, _DATABASE

    try:
        if name is None:
            name = config.config.get('database', 'name')

        if seeds is None:
            seeds = config.config.get('database', 'seeds')

        if max_pool_size is None:
            # we may want to make this configurable, but then again, we may not
            max_pool_size = _DEFAULT_MAX_POOL_SIZE

        _LOG.info("Attempting Database connection with seeds = %s" % (seeds))

        _CONNECTION = pymongo.Connection(seeds, max_pool_size=max_pool_size)
        # Decorate the methods that actually send messages to the db over the
        # network. These are the methods that call start_request, and the
        # decorator causes them call an corresponding end_request
        _CONNECTION._send_message = _end_request_decorator(_CONNECTION._send_message)
        _CONNECTION._send_message_with_response = _end_request_decorator(_CONNECTION._send_message_with_response)

        _DATABASE = getattr(_CONNECTION, name)
        _DATABASE.add_son_manipulator(NamespaceInjector())

        _LOG.info("Database connection established with: seeds = %s, name = %s" % (seeds, name))

    except:
        _LOG.critical('Database initialization failed')
        _CONNECTION = None
        _DATABASE = None
        raise

# -- collection wrapper class --------------------------------------------------

class PulpCollectionFailure(PulpException):
    """
    Exceptions generated by the PulpCollection class
    """


def _retry_decorator(full_name=None, retries=0):
    """
    Collection instance method decorator providing retry support for pymongo
    AutoReconnect exceptions
    :param full_name: the full name of the database collection
    :type  full_name: str
    :param retries: the number of times to retry the operation before allowing 
                    the exception to blow the stack
    :type  retries: int
    """

    def _decorator(method):

        @wraps(method)
        def retry(*args, **kwargs):

            tries = 0

            while tries <= retries:

                try:
                    return method(*args, **kwargs)

                except AutoReconnect:
                    tries += 1

                    _LOG.warn(_('%s operation failed on %s: tries remaining: %d') %
                              (method.__name__, full_name, retries - tries + 1))

                    if tries <= retries:
                        time.sleep(0.3)

            raise PulpCollectionFailure(
                _('%s operation failed on %s: database connection still down after %d tries') %
                (method.__name__, full_name, (retries + 1)))

        return retry

    return _decorator


def _end_request_decorator(method):
    """
    Collection instance method decorator to automatically return the query
    socket to the connection pool once finished
    """

    @wraps(method)
    def _with_end_request(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        finally:
            _CONNECTION.end_request()

    return _with_end_request


class PulpCollection(Collection):
    """
    pymongo.collection.Collection wrapper that provides support for retries when
    pymongo.errors.AutoReconnect exception is raised
    and automatically manages connection sockets for long-running and threaded
    applications
    """

    _decorated_methods = ('get_lasterror_options', 'set_lasterror_options', 'unset_lasterror_options',
                          'insert', 'save', 'update', 'remove', 'drop', 'find', 'find_one', 'count',
                          'create_index', 'ensure_index', 'drop_index', 'drop_indexes', 'reindex',
                          'index_information', 'options', 'group', 'rename', 'distinct', 'map_reduce',
                          'inline_map_reduce', 'find_and_modify')

    def __init__(self, database, name, create=False, retries=0, **kwargs):
        super(PulpCollection, self).__init__(database, name, create=create, **kwargs)

        self.retries = retries

        for m in self._decorated_methods:
            setattr(self, m, _retry_decorator(self.full_name, self.retries)(getattr(self, m)))

    def __getstate__(self):
        return {'name': self.name}

    def __setstate__(self, state):
        return get_collection(state['name'])

    def query(self, criteria):
        """
        Run a query with a Pulp custom query object
        :param criteria: Criteria object specifying the query to run
        :type  criteria: pulp.server.db.model.criteria.Criteria
        :return: pymongo cursor for the given query
        :rtype:  pymongo.cursor.Cursor
        """
        cursor = self.find(criteria.spec, fields=criteria.fields)

        if criteria.sort is not None:
            for entry in criteria.sort:
                cursor.sort(*entry)

        if criteria.skip is not None:
            cursor.skip(criteria.skip)

        if criteria.limit is not None:
            cursor.limit(criteria.limit)

        return cursor

# -- public --------------------------------------------------------------------

def get_collection(name, create=False):
    """
    Factory function to instantiate PulpConnection objects using configurable
    parameters.
    """
    global _DATABASE

    if _DATABASE is None:
        raise PulpCollectionFailure(_('Cannot get collection from uninitialized database'))

    retries = config.config.getint('database', 'operation_retries')
    return PulpCollection(_DATABASE, name, retries=retries, create=create)


def get_database():
    """
    :return: reference to the mongo database being used by the server
    :rtype:  pymongo.database.Database
    """
    return _DATABASE


def get_connection():
    """
    :return: reference to the mongo database connection being used by the server
    :rtype:  pymongo.connection.Connection
    """
    return _CONNECTION


def flush_database(asynchronous=True, lock=False):
    """
    Utility to flush any pending writes to the database.

    If `asynchronous` is true, then the flush will happen asynchronously.
    If `lock` is true, then the database will lock while it is flushed.

    NOTE: `asynchronous` and `lock` may both be false, but only one may be true.

    :param asynchronous: toggle asynchronous behaviour in the flush command
    :type asynchronous: bool
    :param lock: toggle database lock in the flush command
    :type lock: bool
    """
    assert not (asynchronous and lock)

    _CONNECTION.fsync(asyc=asynchronous, lock=lock)
    _CONNECTION.end_request()

