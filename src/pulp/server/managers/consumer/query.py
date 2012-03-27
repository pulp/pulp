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

"""
Contains consumer query classes
"""

from pulp.server.db.model.gc_consumer import Consumer
from pulp.server.exceptions import InvalidValue, MissingResource
from pulp.server.managers import factory
from logging import getLogger


_LOG = getLogger(__name__)


class ConsumerQueryManager(object):

    def find_by_id(self, id):
        """
        Find a consumer by ID.
        @param id: The consumer ID.
        @type id: str
        @return: The consumer model object.
        @rtype: L{Consumer}
        @raise MissingResource: When not found.
        """
        collection = Consumer.get_collection()
        consumer = collection.find_one({'id':id})
        if consumer is None:
            raise MissingResource(id)
        return consumer
