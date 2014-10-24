# -*- coding: utf-8 -*-

import itertools
import logging
import ssl
import time
from gettext import gettext as _

import pymongo
from pymongo.collection import Collection
from pymongo.errors import AutoReconnect
from pymongo.son_manipulator import NamespaceInjector

from pulp.server import config
from pulp.server.compat import wraps
from pulp.server.exceptions import PulpException


_CONNECTION = None
_DATABASE = None
_DEFAULT_MAX_POOL_SIZE = 10
_MONGO_RETRY_TIMEOUT_SECONDS_GENERATOR = itertools.chain([1, 2, 4, 8, 16], itertools.repeat(32))

_logger = logging.getLogger(__name__)


def initialize(name=None, seeds=None, max_pool_size=None, replica_set=None):
    """
    Initialize the connection pool and top-level database for pulp.
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

        _logger.info("Attempting Database connection with seeds = %s" % seeds)
        _logger.info('Connection Arguments: %s' % connection_kwargs)

        # Wait until the Mongo database is available
        while True:
            try:
                _CONNECTION = pymongo.MongoClient(seeds, **connection_kwargs)
            except pymongo.errors.ConnectionFailure as e:
                next_delay = _MONGO_RETRY_TIMEOUT_SECONDS_GENERATOR.next()
                msg = _(
                    "Could not connect to MongoDB at %(url)s:\n%(e)s\n... Waiting "
                    "%(retry_timeout)s seconds and trying again.")
                _logger.error(msg % {'retry_timeout': next_delay, 'url': seeds, 'e': str(e)})
            else:
                break
            time.sleep(next_delay)

        # Decorate the methods that actually send messages to the db over the
        # network. These are the methods that call start_request, and the
        # decorator causes them call an corresponding end_request
        _CONNECTION._send_message = _end_request_decorator(_CONNECTION._send_message)
        _CONNECTION._send_message_with_response = _end_request_decorator(_CONNECTION._send_message_with_response)

        _DATABASE = getattr(_CONNECTION, name)

        # If username & password have been specified in the database config,
        # attempt to authenticate to the database
        if config.config.has_option('database', 'username') and \
                config.config.has_option('database', 'password'):
            username = config.config.get('database', 'username')
            password = config.config.get('database', 'password')
            _logger.info('Database authentication enabled, attempting username/password'
                      'authentication.')
            _DATABASE.authenticate(username, password)
        elif ((config.config.has_option('database', 'username') and
               not config.config.has_option('database', 'password')) or
              (not config.config.has_option('database', 'username') and
               config.config.has_option('database', 'password'))):
            raise Exception("The server config specified username/password authentication but "
                            "is missing either the username or the password")

        _DATABASE.add_son_manipulator(NamespaceInjector())

        # Query the collection names to ensure that we are authenticated properly
        _logger.debug("Querying the database to validate the connection.")
        _DATABASE.collection_names()

        _logger.info("Database connection established with: seeds = %s, name = %s" % (seeds, name))

    except Exception, e:
        _logger.critical('Database initialization failed: %s' % str(e))
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

                    _logger.warn(_('%(method)s operation failed on %(name)s: tries remaining: %(tries)d') %
                              {'method': method.__name__, 'name': full_name,
                               'tries': retries - tries + 1})

                    if tries <= retries:
                        time.sleep(0.3)

            raise PulpCollectionFailure(
                _('%(method)s operation failed on %(name)s: database connection '
                  'still down after %(tries)d tries') %
                {'method': method.__name__, 'name': full_name, 'tries': (retries + 1)})

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
