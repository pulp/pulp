# -*- coding: utf-8 -*-

import copy
import itertools
import logging
import ssl
import time
import warnings
from contextlib import contextmanager
from gettext import gettext as _

import mongoengine
import semantic_version
from pymongo.collection import Collection
from pymongo.errors import AutoReconnect, OperationFailure
from pymongo.son_manipulator import NamespaceInjector

from pulp.common import error_codes
from pulp.server import config
from pulp.server.compat import wraps
from pulp.server.exceptions import PulpCodedException, PulpException


_CONNECTION = None
_DATABASE = None
_DEFAULT_MAX_POOL_SIZE = 10
# please keep this in X.Y.Z format, with only integers.
# see version.cpp in mongo source code for version format info.
MONGO_MINIMUM_VERSION = semantic_version.Version("2.4.0")
MONGO_WRITE_CONCERN_VERSION = semantic_version.Version("2.6.0")

_logger = logging.getLogger(__name__)


def initialize(name=None, seeds=None, max_pool_size=None, replica_set=None, max_timeout=32):
    """
    Initialize the connection pool and top-level database for pulp. Calling this more than once will
    raise a RuntimeError.

    :param max_timeout:   the maximum number of seconds to wait between
                          connection retries
    :type  max_timeout:   int
    :raises RuntimeError: This Exception is raised if initialize is called more than once
    """
    global _CONNECTION, _DATABASE

    # We do not allow a second call to initialize(), as mongoengine.connect() will cache the last
    # initialized connection for all calls. Thus, any process that attempts to call initialize()
    # again might alter which database all further queries are made against. By raising this
    # Exception, we can ensure that only one database connection is established per process which
    # will help us to ensure that the connection does not get overridden later.
    if _CONNECTION or _DATABASE:
        raise RuntimeError("The database is already initialized. It is an error to call this "
                           "function a second time.")

    try:
        connection_kwargs = {}

        if name is None:
            name = config.config.get('database', 'name')

        if seeds is None:
            seeds = config.config.get('database', 'seeds')
        seeds_list = seeds.split(',')

        if max_pool_size is None:
            # we may want to make this configurable, but then again, we may not
            max_pool_size = _DEFAULT_MAX_POOL_SIZE
        connection_kwargs['maxPoolSize'] = max_pool_size

        if replica_set is None:
            if config.config.has_option('database', 'replica_set'):
                replica_set = config.config.get('database', 'replica_set')

        if replica_set is not None:
            connection_kwargs['replicaSet'] = replica_set

        write_concern = config.config.get('database', 'write_concern')
        if write_concern not in ['majority', 'all']:
            raise PulpCodedException(error_code=error_codes.PLP0043)
        elif write_concern == 'all':
            write_concern = len(seeds_list)

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

        # If username & password have been specified in the database config,
        # attempt to authenticate to the database
        username = config.config.get('database', 'username')
        password = config.config.get('database', 'password')
        if username:
            _logger.debug(_('Attempting username and password authentication.'))
            connection_kwargs['username'] = username
            connection_kwargs['password'] = password
        elif password and not username:
            raise Exception(_("The server config specified a database password, but is "
                              "missing a database username."))

        # Wait until the Mongo database is available
        mongo_retry_timeout_seconds_generator = itertools.chain([1, 2, 4, 8, 16],
                                                                itertools.repeat(32))

        if seeds != '':
            if len(seeds_list) > 1 and not replica_set:
                raise PulpCodedException(error_code=error_codes.PLP0041)
            while True:
                _CONNECTION = _connect_to_one_of_seeds(connection_kwargs, seeds_list, name)
                if _CONNECTION:
                    db_version = semantic_version.Version(_CONNECTION.server_info()['version'])
                    if db_version < MONGO_MINIMUM_VERSION:
                        raise RuntimeError(_("Pulp requires Mongo version %s, but DB is reporting"
                                             "version %s") % (MONGO_MINIMUM_VERSION,
                                                              db_version))
                    if 'w' not in connection_kwargs:
                        # We need to use the mongod version to determine what value to set the
                        # write_concern to.
                        if db_version >= MONGO_WRITE_CONCERN_VERSION or replica_set:
                            # Write concern of 'majority' only works with a replica set or when
                            # using MongoDB >= 2.6.0
                            connection_kwargs['w'] = write_concern
                        else:
                            connection_kwargs['w'] = 1
                        # Now that we've determined the write concern that we are allowed to use, we
                        # must drop this connection and get another one because write_concern can
                        # only be set upon establishing the connection in pymongo >= 3.
                        _CONNECTION.close()
                        _CONNECTION = None
                        continue
                    _logger.info(_("Write concern for Mongo connection: %s") %
                                 _CONNECTION.write_concern.document)
                    break
                else:
                    next_delay = min(mongo_retry_timeout_seconds_generator.next(), max_timeout)
                    msg = _("Could not connect to any of MongoDB seeds at %(url)s:\n... Waiting "
                            "%(retry_timeout)s seconds and trying again.")
                    _logger.error(msg % {'retry_timeout': next_delay, 'url': seeds})
                    time.sleep(next_delay)
        else:
            raise PulpCodedException(error_code=error_codes.PLP0040)

        try:
            _DATABASE = mongoengine.connection.get_db()
        except OperationFailure as error:
            if error.code == 18:
                msg = _('Authentication to MongoDB '
                        'with username and password failed.')
                raise RuntimeError(msg)

        _DATABASE.add_son_manipulator(NamespaceInjector())

        # Query the collection names to ensure that we are authenticated properly
        _logger.debug(_('Querying the database to validate the connection.'))
        _DATABASE.collection_names()
    except Exception, e:
        _logger.critical(_('Database initialization failed: %s') % str(e))
        _CONNECTION = None
        _DATABASE = None
        raise


@contextmanager
def suppress_connect_warning(logger):
    """
    A context manager that will suppress pymongo's connect before fork warning

    python's warnings module gives you a way to filter warnings (warnings.filterwarnings),
    and a way to catch warnings (warnings.catch_warnings), but not a way to do both. This
    context manager filters out the specific python warning about connecting before fork,
    while allowing all other warnings to normally be issued, so they aren't covered up
    by this context manager.

    The behavior seen here is based on the warnings.catch_warnings context manager, which
    also works by stashing the original showwarnings function and replacing it with a custom
    function while the context is entered.

    Outright replacement of functions in the warnings module is recommended by that module.

    The logger from the calling module is used to help identify which call to
    this context manager suppressed the pymongo warning.

    :param logger: logger from the module using this context manager
    :type logger: logging.Logger
    """
    try:
        warning_func_name = warnings.showwarning.func_name
    except AttributeError:
        warning_func_name = None

    # if the current showwarning func isn't already pymongo_suppressing_showwarning, replace it.
    # checking this makes this context manager reentrant with itself, since it won't replace
    # showwarning functions already replaced by this CM, but will replace all others
    if warning_func_name != 'pymongo_suppressing_showwarning':
        original_showwarning = warnings.showwarning

        # this is effectively a functools.partial used to generate a version of the warning catcher
        # using the passed-in logger and original showwarning function, but the logging module
        # rudely checks the type before calling this, and does not accept partials
        def pymongo_suppressing_showwarning(*args, **kwargs):
            return _pymongo_warning_catcher(logger, original_showwarning, *args, **kwargs)

        try:
            # replace warnings.showwarning with our pymongo warning catcher,
            # using the passed-in logger and the current showwarning function
            warnings.showwarning = pymongo_suppressing_showwarning
            yield
        finally:
            # whatever happens, restore the original showwarning function
            warnings.showwarning = original_showwarning
    else:
        # showwarning already replaced outside this context manager, nothing to do
        yield


def _pymongo_warning_catcher(logger, showwarning, message, category, *args, **kwargs):
    """
    An implementation of warnings.showwarning that supresses pymongo's connect before work warning

    This is intended to be wrapped with functools.partial by the mechanism that replaces
    the warnings.showwarnings function, with the first two args being a list in which to store
    the caught pymongo warning(s), and the second being the original warnings.showwarnings
    function, through which all other warnings will be passed.

    :param caught: list to be populated with caught warnings for inspection in the caller
    :type caught: list
    :param showwarning: The "real" warnings.showwarning function, for passing unrelated warnings
    :type showwarning: types.FunctionType

    All remaining args are the same as warnings.showwarning, and are only used here for filtering
    """
    message_expected = 'MongoClient opened before fork'
    # message is an instance of category, which becomes the warning message when cast as str
    if category is UserWarning and message_expected in str(message):
        # warning is pymongo connect before fork warning, log it...
        logger.debug('pymongo reported connection before fork, ignoring')
        # ...and filter it out for the rest of this process's lifetime
        warnings.filterwarnings('ignore', message_expected)
    else:
        # not interested in this warning, run it through the provided showwarning function
        showwarning(message, category, *args, **kwargs)


def _connect_to_one_of_seeds(connection_kwargs, seeds_list, db_name):
    """
    Helper function to iterate over a list of database seeds till a successful connection is made

    :param connection_kwargs: arguments to pass to mongoengine connection
    :type connection_kwargs: dict
    :param seeds_list: list of seeds to try connecting to
    :type seeds_list: list of strings
    :return: Connection object if connection is made or None if no connection is made
    """
    connection_kwargs = copy.deepcopy(connection_kwargs)
    for seed in seeds_list:
        connection_kwargs.update({'host': seed.strip()})
        try:
            _logger.info("Attempting to connect to %(host)s" % connection_kwargs)
            shadow_connection_kwargs = copy.deepcopy(connection_kwargs)
            if connection_kwargs.get('password'):
                shadow_connection_kwargs['password'] = '*****'
            _logger.debug(_('Connection Arguments: %s') % shadow_connection_kwargs)
            connection = mongoengine.connect(db_name, **connection_kwargs)
            return connection
        except mongoengine.connection.ConnectionError as e:
            msg = _("Could not connect to MongoDB at %(url)s:\n%(e)s\n")
            _logger.info(msg % {'url': seed, 'e': str(e)})


class PulpCollectionFailure(PulpException):
    """
    Exceptions generated by the PulpCollection class
    """


class UnsafeRetry(object):
    """
    Class that decorates PyMongo to retry in the event of AutoReconnect exceptions.
    """

    _decorated_methods = ('get_lasterror_options', 'set_lasterror_options',
                          'unset_lasterror_options', 'insert', 'save', 'update', 'remove', 'drop',
                          'find', 'find_one', 'count', 'create_index', 'ensure_index',
                          'drop_index', 'drop_indexes', 'reindex', 'index_information', 'options',
                          'group', 'rename', 'distinct', 'map_reduce', 'inline_map_reduce',
                          'find_and_modify')

    @classmethod
    def decorate_instance(cls, instance, full_name):
        """
        Decorate the PyMongo methods on instance.

        :param instance: instance of a class that implements PyMongo methods.
        :type  instance: pulp.server.db.PulpCollection or pulp.server.db.model.AutoRetryDocument
        :param full_name: Collection of the class, used for logging
        :type  full_name: str
        """

        unsafe_autoretry = config.config.getboolean('database', 'unsafe_autoretry')
        if unsafe_autoretry:
            for m in cls._decorated_methods:
                try:
                    setattr(instance, m, cls.retry_decorator(full_name)(getattr(instance, m)))
                except AttributeError:
                    pass

    @staticmethod
    def retry_decorator(full_name=None):
        """
        Recorator providing retry support for pymongo AutoReconnect exceptions.

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
                        msg = _('%(method)s operation failed on %(name)s') % {
                            'method': method.__name__, 'name': full_name}
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

    def __init__(self, database, name, create=False, **kwargs):
        super(PulpCollection, self).__init__(database, name, create=create, **kwargs)
        UnsafeRetry.decorate_instance(instance=self, full_name=self.full_name)

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
        cursor = self.find(criteria.spec, projection=criteria.fields)

        if criteria.sort is not None:
            for entry in criteria.sort:
                cursor.sort(*entry)

        if criteria.skip is not None:
            cursor.skip(criteria.skip)

        if criteria.limit is not None:
            cursor.limit(criteria.limit)

        return cursor


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
