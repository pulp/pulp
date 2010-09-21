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
Contains (proxy) classes that represent the pulp agent.
The proxy classes must match the names of classes that are exposed
on the agent.
"""

from pulp.messaging.base import Container
from pulp.messaging.producer import Producer
from pulp.server.config import config


class Agent(Container):
    """
    A collection of stubs that represent the agent.
    """

    def __init__(self, uuid, **options):
        """
        @param uuid: The consumer uuid.
        @type uuid: str|list
        @param options: Messaging L{pulp.messaging.Options}
        """
        url = config.get('messaging', 'url')
        self.__producer = Producer(url=url)
        Container.__init__(self, uuid, self.__producer, **options)

    def delete(self):
        """
        Delete all messaging resources.
        """
        queue = self._Container__destination()
        if isinstance(queue, (list, tuple)):
            raise Exception, 'group delete, not permitted'
        session = self.__producer.session()
        queue.delete(session)
