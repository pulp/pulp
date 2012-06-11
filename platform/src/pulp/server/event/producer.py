#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

"""
Contains QPID event producer classes.
"""

from gofer.messaging import Topic
from gofer.messaging.producer import Producer


class EventProducer(Producer):
    """
    Event producer.
    """

    def send(self, subject, event):
        """
        Send an event.
        @param subject: A subject.
        @type subject: str
        @param event: The event body
        @type event: object
        """
        destination = Topic('event', subject)
        Producer.send(self, destination, event=event)
