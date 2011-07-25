#!/usr/bin/python
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

from pulp.client.lib.plugins.errata import ErrataAction, Errata, List
from pulp.client.logutil.lib import getLogger

log = getLogger(__name__)

# errata actions --------------------------------------------------------------

class ConsumerList(List):

    def run(self):
        consumerid = self.getconsumerid()
        repoid = self.opts.repoid

        # If running the consumer client, let the repo ID override the consumer's retrieved ID
        if self.is_consumer_client and repoid:
            consumerid = None

        List.run(self, consumerid)


# errata command --------------------------------------------------------------

class ConsumerErrata(Errata):

    actions = [ ConsumerList ]


# errata plugin --------------------------------------------------------------

class ConsumerErrataPlugin(ConsumerPlugin):
    
    commands = [ ConsumerErrata ]
