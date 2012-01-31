#
# Pulp Repo management module
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

from pulp.client.consumer.credentials import Consumer as ConsumerBundle
from pulp.client.consumer.plugin import ConsumerPlugin
from pulp.client.plugins.errata import ErrataAction, Errata, List
from pulp.client.lib.logutil import getLogger

log = getLogger(__name__)

# errata actions --------------------------------------------------------------

class ConsumerList(List):

    @property
    def consumerid(self):
        """
        Get the consumer ID from the identity certificate.
        @return: The consumer id.  Returns (None) when not registered.
        @rtype: str
        """
        bundle = ConsumerBundle()
        return bundle.getid()

    def run(self):
        consumerid = self.consumerid
        repoid = self.opts.repoid

        List.run(self, consumerid)

    def getconsumerid(self):
        """
        Get the consumer ID from the identity certificate.
        @return: The consumer id.  Returns (None) when not registered.
        @rtype: str
        """
        bundle = ConsumerBundle()
        return bundle.getid()

# errata command --------------------------------------------------------------

class ConsumerErrata(Errata):

    actions = [ ConsumerList ]

# errata plugin --------------------------------------------------------------

class ConsumerErrataPlugin(ConsumerPlugin):
    
    name = "errata"
    commands = [ ConsumerErrata ]
