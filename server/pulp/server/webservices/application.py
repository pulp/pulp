import logging
import sys

# We need to read the config prior to any other imports, since some of the imports will invoke
# setup methods. Importing the config reads the config file, unfortunately.
from pulp.server import config  # noqa
from pulp.server import initialization, logs
from pulp.server.agent.direct.services import Services as AgentServices
# Even though this import does not get used anywhere, we must import it for the Celery
# application to be initialized.
from pulp.server.async import app as celery_app  # noqa
from pulp.server.db.migrate import models as migration_models
from pulp.server.webservices.http import _thread_local
from pulp.server.webservices.wsgi import application as django_application


logger = logging.getLogger(__name__)
_IS_INITIALIZED = False

STACK_TRACER = None


class SaveEnvironWSGIHandler(object):
    """
    A WSGI handler called before Django which saves a reference to environ in http._thread_local.
    This saved reference is accessed throughout the Pulp codebase. For more info on how WSGI is
    implemented in Python see [0].

    [0]: https://www.python.org/dev/peps/pep-3333/
    """

    def __init__(self, django_wsgi):
        """
        Initializes a SaveEnvironWSGIHandler object with an django_wsgi handler.

        :param django_wsgi: A WSGI object for Django
        :type django_wsgi: A WSGI compatible object
        """
        self.django_wsgi = django_wsgi

    def __call__(self, environ, start_response):
        """
        A WSGI handler that saves a reference to environ in http._thread_local
        """
        _thread_local.wsgi_environ = environ
        return self.django_wsgi(environ, start_response)


def _initialize_web_services():
    """
    This function initializes Pulp for webservices.
    """

    # This initialization order is very sensitive, and each touches a number of
    # sub-systems in pulp. If you get this wrong, you will have pulp tripping
    # over itself on start up.

    global _IS_INITIALIZED, STACK_TRACER
    if _IS_INITIALIZED:
        return

    logs.start_logging()

    # Run the common initialization code that all processes should share. This will start the
    # database connection, initialize plugins, and initialize the manager factory.
    initialization.initialize()

    # configure agent services
    AgentServices.init()

    # Verify the database has been migrated to the correct version. This is
    # very likely a reason the server will fail to start.
    try:
        migration_models.check_package_versions()
    except Exception:
        msg = 'The database has not been migrated to the current version. '
        msg += 'Run pulp-manage-db and restart the application.'
        raise initialization.InitializationException(msg), None, sys.exc_info()[2]

    # There's a significantly smaller chance the following calls will fail.
    # The previous two are likely user errors, but the remainder represent
    # something gone horribly wrong. As such, I'm not going to account for each
    # and instead simply let the exception itself bubble up.

    # start agent services
    AgentServices.start()

    # If we got this far, it was successful, so flip the flag
    _IS_INITIALIZED = True


def wsgi_application():
    """
    Application factory to create, configure, and return a WSGI application
    using the django framework and custom Pulp middleware.
    @return: wsgi application callable
    """

    # The following intentionally don't raise the exception. The logging writes
    # to both error_log and pulp.log. Raising the exception caused it to be
    # logged twice to error_log, which was annoying. The Pulp server still
    # fails to start (I can't even log in), and on attempts to use it the
    # initialize failure message is logged again. I like that behavior so I
    # think this approach makes sense. But if there is a compelling reason to
    # raise the exception, change it; I don't have a strong conviction behind
    # this approach other than the duplicate logging and the appearance that it
    # works as desired.
    # jdob, Nov 21, 2012

    try:
        _initialize_web_services()
    except initialization.InitializationException, e:
        logger.fatal('*************************************************************')
        logger.fatal('The Pulp server failed to start due to the following reasons:')
        logger.exception('  ' + e.message)
        logger.fatal('*************************************************************')
        raise e
    except Exception as e:
        logger.fatal('*************************************************************')
        logger.exception('The Pulp server encountered an unexpected failure during initialization')
        logger.fatal('*************************************************************')
        raise e

    logger.info('*************************************************************')
    logger.info('The Pulp server has been successfully initialized')
    logger.info('*************************************************************')

    return SaveEnvironWSGIHandler(django_application)
