#! /usr/bin/env python
#
# Copyright (c) 2010 Red Hat, Inc.
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
#

"""
Contains QPID event consumer classes.
"""

from gofer.messaging import Topic
from gofer.messaging.consumer import Consumer
from logging import getLogger

log = getLogger(__name__)


class EventConsumer(Consumer):
    """
    An AMQP event consumer.
    """

    def __init__(self, subject=None, name=None, **other):
        """
        @param subject: An (optional) event subject.
        @type subject: str
        """
        topic = Topic('event', subject, name)
        Consumer.__init__(self, topic, **other)

    def dispatch(self, envelope):
        """
        Process received request.
        @param envelope: The received envelope.
        @type envelope: L{Envelope}
        """
        try:
            subject = envelope.subject
            body = envelope.event
            self.raised(subject, body)
        except Exception, e:
            log.exception(e)
        self.ack()

    def raised(self, subject, event):
        """
        Notify the listener that an event has been raised.
        @param subject: The event subject.
        @type subject: str
        @param event: The event body.
        @type event: any
        """
        pass
