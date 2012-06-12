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
Contains content management classes
"""

from pulp.server.db.model.consumer import Consumer
from pulp.server.exceptions import InvalidValue, MissingResource
from pulp.server.agent import PulpAgent
from logging import getLogger


_LOG = getLogger(__name__)


class ConsumerContentManager(object):
    """
    Provies content management on a consumer
    """
    
    def install(self, id, units, options={}):
        """
        Install content on a consumer.
        @param id: A consumer id.
        @type id: str
        @param units: A list of content units to be installed.
        @type units: list of:
            { type_id:<str>, metadata:<dict> }
        @param options: Install options; based on unit type.
        @type options: dict
        """
        collection = Consumer.get_collection() 
        consumer = collection.find_one({'id':id})
        if consumer is None:
            raise MissingResource(id)
        agent = PulpAgent(consumer)
        agent.install_units(units, options)
    
    def update(self, id, units, options={}):
        """
        Update content on a consumer.
        @param id: A consumer id.
        @type id: str
        @param units: A list of content units to be updated.
        @type units: list of:
            { type_id:<str>, metadata:<dict> }
        @param options: Update options; based on unit type.
        @type options: dict
        """
        collection = Consumer.get_collection() 
        consumer = collection.find_one({'id':id})
        if consumer is None:
            raise MissingResource(id)
        agent = PulpAgent(consumer)
        agent.update_units(units, options)
    
    def uninstall(self, id, units, options={}):
        """
        Uninstall content on a consumer.
        @param id: A consumer id.
        @type id: str
        @param units: A list of content units to be uninstalled.
        @type units: list of:
            { type_id:<str>, metadata:<dict> }
        @param options: Uninstall options; based on unit type.
        @type options: dict
        """
        collection = Consumer.get_collection() 
        consumer = collection.find_one({'id':id})
        if consumer is None:
            raise MissingResource(id)
        agent = PulpAgent(consumer)
        agent.uninstall_units(units, options)
