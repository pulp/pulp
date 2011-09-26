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

from pulp.repo_auth.repo_cert_utils import M2CRYPTO_HAS_CRL_SUPPORT
from pulp.server.logs import start_logging
from pulp.server.event.dispatcher import EventDispatcher
from pulp.server.agent import HeartbeatListener
from pulp.server.async import ReplyHandler, WatchDog
from pulp.server.config import config
import pulp.server.content.loader as plugin_loader
import pulp.server.db.connection as db_connection
import pulp.server.managers.factory as manager_factory
from gofer.messaging.broker import Broker

# start logging
start_logging()
LOG = logging.getLogger(__name__)

if not M2CRYPTO_HAS_CRL_SUPPORT:
    LOG.warning("M2Crypto lacks needed CRL functionality, therefore CRL checking will be disabled.")

# configure AMQP broker
url = config.get('messaging', 'url')
broker = Broker(url)
broker.cacert = config.get('messaging', 'cacert')
broker.clientcert = config.get('messaging', 'clientcert')

# start the event dispatcher
if config.getboolean('events', 'recv_enabled'):
    dispatcher = EventDispatcher()
    dispatcher.start()

# start async message timeout watchdog
watchdog = WatchDog(url=url)
watchdog.start()

# start async task reply handler
replyHandler = ReplyHandler(url)
replyHandler.start(watchdog)

# start agent heartbeat listener
heartbeatListener = HeartbeatListener(url)
heartbeatListener.start()

# Initialize the manager factory class mappings
manager_factory.initialize()

# Initialize the database
db_connection.initialize()

# Initialize the content manager
plugin_loader.initialize()
