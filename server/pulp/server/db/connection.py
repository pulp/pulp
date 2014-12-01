# -*- coding: utf-8 -*-

import itertools
import logging
import ssl
import time
from gettext import gettext as _

import mongoengine
from pymongo.collection import Collection
from pymongo.errors import AutoReconnect
from pymongo.son_manipulator import NamespaceInjector

from pulp.server import config
from pulp.server.compat import wraps
from pulp.server.exceptions import PulpException


_CONNECTION = None
_DATABASE = None
_DEFAULT_MAX_POOL_SIZE = 10
# please keep this in X.Y.Z format, with only integers.
# see version.cpp in mongo source code for version format info.
MONGO_MINIMUM_VERSION = "2.4.0"


_logger = logging.getLogger(__name__)


def initialize(name=None, seeds=None, max_pool_size=None, replica_set=None, max_timeout=32):
    """
    Initialize the connection pool and top-level database for pulp.

    :param max_timeout: the maximum number of seconds to wait between
                        connection retries
    :type  max_timeout: int
    """
    global _CONNECTION, _DATABASE

    try:
        connection_kwargs = {}

        if name is None:
            name = config.config.get('database', 'name')

        if seeds is None:
            seeds = config.config.get('database', 'seeds')

        if max_pool_size is None:
            # we may want to make this configurable, but then again, we may not
            max_pool_size = _DEFAULT_MAX_POOL_SIZE
        connection_kwargs['max_pool_size'] = max_pool_size

        if replica_set is None:
            if config.config.has_option('database', 'replica_set'):
                replica_set = config.config.get('database', 'replica_set')

        if replica_set is not None:
            connection_kwargs['replicaset'] = replica_set

        # Process SSL settings
        if config.config.getboolean('database', 'ssl'):
            connection_kwargs['ssl'] = True
            ssl_keyfile = config.config.get('database', 'ssl_keyfile')
            ssl_certfile = config.config.get('database', 'ssl_certfile')
            if ssl_keyfile:
                connection_kwargs['ssl_keyfile'] = ssl_keyfile
            if ssl_certfile:
                connection_kwargs['ssl_certfile'] = ssl_certfile
            verify_ssl = config.config.getboolean('database', 'verify_ssl')
            connection_kwargs['ssl_cert_reqs'] = ssl.CERT_REQUIRED if verify_ssl else ssl.CERT_NONE
            connection_kwargs['ssl_ca_certs'] = config.config.get('database', 'ca_path')

        _logger.debug(_('Attempting Database connection with seeds = %s') % seeds)
        _logger.debug(_('Connection Arguments: %s') % connection_kwargs)

        # Wait until the Mongo database is available
        mongo_retry_timeout_seconds_generator = itertools.chain([1, 2, 4, 8, 16], itertools.repeat(32))
        while True:
            try:
                _CONNECTION = mongoengine.connect(seeds, **connection_kwargs)
            except mongoengine.connection.ConnectionError as e:
                next_delay = min(mongo_retry_timeout_seconds_generator.next(), max_timeout)
                msg = _(
                    "Could not connect to MongoDB at %(url)s:\n%(e)s\n... Waiting "
                    "%(retry_timeout)s seconds and trying again.")
                _logger.error(msg % {'retry_timeout': next_delay, 'url': seeds, 'e': str(e)})
            else:
                break
            time.sleep(next_delay)

        _DATABASE = getattr(_CONNECTION, name)

        # If username & password have been specified in the database config,
        # attempt to authenticate to the database
        username = config.config.get('database', 'username')
        password = config.config.get('database', 'password')
        if username and password:
            _logger.debug(_('Database authentication enabled, attempting username/password'
                            ' authentication.'))
            _DATABASE.authenticate(username, password)
        elif (username and not password) or (password and not username):
            raise Exception(_("The server config specified username/password authentication but "
                            "is missing either the username or the password"))

        _DATABASE.add_son_manipulator(NamespaceInjector())

        # Query the collection names to ensure that we are authenticated properly
        _logger.debug(_('Querying the database to validate the connection.'))
        _DATABASE.collection_names()

        db_version = _CONNECTION.server_info()['version']
        _logger.info(_("Mongo database for connection is version %s") % db_version)

        db_version_tuple = tuple(db_version.split("."))
        db_min_version_tuple = tuple(MONGO_MINIMUM_VERSION.split("."))
        if db_version_tuple < db_min_version_tuple:
            raise RuntimeError(_("Pulp requires Mongo version %s, but DB is reporting version %s") %
                               (MONGO_MINIMUM_VERSION, db_version))

        _logger.debug(
            _("Database connection established with: seeds = %(seeds)s, name = %(name)s") %
            {'seeds': seeds, 'name': name}
        )

    except Exception, e:
        _logger.critical(_('Database initialization failed: %s') % str(e))
        _CONNECTION = None
        _DATABASE = None
        raise


class PulpCollectionFailure(PulpException):
    """
    Exceptions generated by the PulpCollection class
    """


def retry_decorator(full_name=None):
    """
    Collection instance method decorator providing retry support for pymongo
    AutoReconnect exceptions

    :param full_name: the full name of the database collection
    :type  full_name: str
    """

    def _decorator(method):

        @wraps(method)
        def retry(*args, **kwargs):
            while True:
                try:
                    return method(*args, **kwargs)

                except AutoReconnect:
                    msg = _('%(method)s operation failed on %(name)s') % {'method': method.__name__,
                                                                          'name': full_name}
                    _logger.error(msg)

                    time.sleep(0.3)

        return retry

    return _decorator


class PulpCollection(Collection):
    """
    pymongo.collection.Collection wrapper that provides auto-retry support when
    pymongo.errors.AutoReconnect exception is raised
    and automatically manages connection sockets for long-running and threaded
    applications
    """

    _decorated_methods = ('get_lasterror_options', 'set_lasterror_options', 'unset_lasterror_options',
                          'insert', 'save', 'update', 'remove', 'drop', 'find', 'find_one', 'count',
                          'create_index', 'ensure_index', 'drop_index', 'drop_indexes', 'reindex',
                          'index_information', 'options', 'group', 'rename', 'distinct', 'map_reduce',
                          'inline_map_reduce', 'find_and_modify')

    def __init__(self, database, name, create=False, **kwargs):
        super(PulpCollection, self).__init__(database, name, create=create, **kwargs)

        for m in self._decorated_methods:
            setattr(self, m, retry_decorator(self.full_name)(getattr(self, m)))

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

    return PulpCollection(_DATABASE, name, create=create)


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
