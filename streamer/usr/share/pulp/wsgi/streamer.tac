import ConfigParser
import logging
import os
import sys

import mongoengine
from twisted.application import internet, service
from twisted.web import server

from pulp.server.logs import CompliantSysLogHandler
from pulp.server.db.connection import initialize as mongo_initialize
from pulp.streamer import Streamer, load_configuration, DEFAULT_CONFIG_FILES
from pulp.plugins.loader import api as plugin_api


DEFAULT_LOG_LEVEL = logging.INFO
LOG_FORMAT_STRING = 'pulp_streamer: %(name)s:%(levelname)s: %(message)s'
LOG_PATH = os.path.join('/', 'dev', 'log')


def start_logging(config):
    """
    Configure the Pulp streamer syslog handler for the configured log level.
    """
    # Get and set up the root logger with our configured log level
    try:
        log_level = config.get('streamer', 'log_level')
        log_level = getattr(logging, log_level.upper())
    except (ConfigParser.NoOptionError, AttributeError):
        # If the user didn't provide a log level, or if they provided an
        # invalid one, let's use the default log level
        log_level = DEFAULT_LOG_LEVEL
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Set up our handler and add it to the root logger
    if not os.path.exists(LOG_PATH):
        print >> sys.stderr, "Unable to access to log, {log_path}.".format(log_path=LOG_PATH)
        sys.exit(os.EX_UNAVAILABLE)

    handler = CompliantSysLogHandler(address=LOG_PATH,
                                     facility=CompliantSysLogHandler.LOG_DAEMON)
    formatter = logging.Formatter(LOG_FORMAT_STRING)
    handler.setFormatter(formatter)
    root_logger.handlers = []
    root_logger.addHandler(handler)


# Initialization of application dependencies.
streamer_config = load_configuration(DEFAULT_CONFIG_FILES)
start_logging(streamer_config)
mongo_initialize()
mongoengine.connect('pulp_database')
plugin_api.initialize()

# Configure the twisted application itself.
application = service.Application('Pulp Streamer')
site = server.Site(Streamer(streamer_config))
service_collection = service.IServiceCollection(application)
port = streamer_config.get('streamer', 'port')
interfaces = streamer_config.get('streamer', 'interfaces')
if interfaces:
    for interface in interfaces.split(','):
        i = internet.TCPServer(int(port), site, interface=interface.strip())
        i.setServiceParent(service_collection)
else:
    # If not defined, listen on all interfaces
    i = internet.TCPServer(int(port), site)
    i.setServiceParent(service_collection)
