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

from pulp.server.db.model.gc_base import Model

# -- classes -----------------------------------------------------------------

class Consumer(Model):
    """
    Represents a consumer for the content on Pulp server.

    @ivar id: uniquely identifies the consumer
    @type id: str

    @ivar display_name: user-friendly name of the consumer
    @type display_name: str

    @ivar description: user-friendly description of the consumer
    @type description: str

    @ivar notes: arbitrary key-value pairs programmatically describing the consumer
    @type notes: dict
    """

    collection_name = 'gc_consumers'
    unique_indices = ('id',)

    def __init__(self, id, display_name, description=None, notes=None, capabilities=None, certificate=None):
        super(Consumer, self).__init__()

        self.id = id
        self.display_name = display_name
        self.description = description
        self.notes = notes or {}

        self.capabilities = capabilities or {}
        self.certificate = certificate or None
        self.unit_profile = []
        self.repo_ids = []
