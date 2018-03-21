import ConfigParser
import logging
import os
import sys

import mongoengine
from twisted.application import internet, service
from twisted.web import server

from pulp.server.logs import start_logging
from pulp.server.db.connection import initialize as mongo_initialize
from pulp.server.managers import factory as manager_factory
from pulp.streamer import Streamer, load_configuration, DEFAULT_CONFIG_FILES
from pulp.plugins.loader import api as plugin_api


DEFAULT_LOG_LEVEL = logging.INFO
LOG_FORMAT_STRING = 'pulp_streamer: %(name)s:%(levelname)s: %(message)s'

# Initialization of application dependencies.
streamer_config = load_configuration(DEFAULT_CONFIG_FILES)
start_logging()
mongo_initialize()
mongoengine.connect('pulp_database')
plugin_api.initialize()
manager_factory.initialize()

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
