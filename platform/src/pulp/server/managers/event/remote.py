# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
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

from qpid.messaging import Connection
from qpid.messaging.exceptions import ConnectionError, MessagingError

from pulp.common.json_compat import json
from pulp.server.config import config


class TopicPublishManager(object):
    BASE_TOPIC = 'pulp.server'
    EXCHANGE = config.get('messaging', 'topic_exchange')

    _connection = None
    _logged_disabled = False
    logger = logging.getLogger(__name__)

    @classmethod
    def _disabled_message(cls):
        """
        Only write a log message once to say that messaging is disabled, because
        otherwise this could be very noisy.
        """
        if not cls._logged_disabled:
            cls.logger.debug(
                'remote messaging is disabled because no server was specified')
            cls._logged_disabled = True

    @classmethod
    def connection(cls):
        """
        :return:    An open connection object if available, or else None.
        :rtype:     qpid.messaging.Connection
        """
        if not cls._connection:
            address = config.get('messaging', 'url')
            if not address:
                cls._disabled_message()
                return
            cls._connection = Connection(address, reconnect=True)
            try:
                cls._connection.open()
            except ConnectionError, e:
                # log the error, but allow life to go on.
                cls.logger.error(
                    'could not connect to messaging server %s' % address)
                return

        return cls._connection

    @classmethod
    def publish(cls, event):
        """
        Publish an event to a remote exchange. This sends the JSON-serialized
        version of the output from the event's "data" method as the content
        of the message.

        Failures to publish a message will be logged but will not

        :param event: the event that should be published to a remote exchange
        :type  event: pulp.server.event.data.Event
        """
        connection = cls.connection()
        if connection:
            topic = '%s.%s' % (cls.BASE_TOPIC, event.event_type)
            destination = '%s/%s' % (cls.EXCHANGE, topic)
            data = json.dumps(event.data())
            try:
                cls.connection().session().sender(destination).send(data)
            except MessagingError, e:
                # log the error, but allow life to go on.
                cls.logger.error('could not publish message: %s' % str(e))
