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

from pulp.server.managers import factory

TYPE_ID = 'amqp'
logger = logging.getLogger(__name__)

def handle_event(notifier_config, event):
    """
    Send the event out to an AMQP broker.

    :param notifier_config: dictionary with keys 'subject', which defines the
                            subject of each email message, and 'addresses',
                            which is a list of strings that are email addresses
                            that should receive this notification.
    :type  notifier_config: dict
    :param event:   Event instance
    :type  event:   pulp.server.event.data.event
    :return: None
    """

    factory.topic_publish_manager().publish(event, notifier_config.get('exchange'))
