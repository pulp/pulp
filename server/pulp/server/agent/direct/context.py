# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import hashlib

from pulp.server.config import config as pulp_conf

from pulp.server.agent.direct.services import Services


class Context(object):
    """
    The remote method invocation context provides call
    context sensitive options and settings.
    :ivar uuid: The agent UUID.
    :type uiud: str
    :ivar url: The broker URL.
    :type url: str
    :ivar secret: The server agent shared secret for the consumer.
    :type secret: str
    :ivar round_tripped: Data round tripped to that agent and back.
        Used by the reply consumer.
    :type round_tripped: object
    :ivar watchdog: A gofer watchdog object.  Used to track overdue requests.
    :type watchdog: gofer.rmi.async.Watchdog
    :ivar ctag: The reply correlation tag.
    :type ctag: str
    """

    def __init__(self, consumer, **details):
        """
        :param consumer: A consumer DB model object.
        :type consumer: dict
        """
        self.uuid = consumer['id']
        self.url = pulp_conf.get('messaging', 'url')
        certificate = consumer.get('certificate')
        hash = hashlib.sha256()
        hash.update(certificate.strip())
        self.secret = hash.hexdigest()
        self.details = details
        self.watchdog = Services.watchdog
        self.ctag = Services.CTAG

    @staticmethod
    def get_timeout(option):
        """
        Get a timeout option from the server configuration.
        The value is parsed and converted into a gofer
        timeout tuple.
        :param option: The name of a config option.
        :type option: str
        :return: A gofer timeout tuple: (<initial>, <duration>).
        :rtype tuple
        """
        value = pulp_conf.get('messaging', option)
        initial, duration = value.split(':')
        return initial, duration
