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
Contains manager class and exceptions for operations surrounding consumer notes.
"""

import logging

from pulp.server.db.model.gc_consumer import Consumer
from pulp.server.exceptions import InvalidValue, MissingResource

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- manager ------------------------------------------------------------------

class ConsumerNotesManager(object):
    """
    Performs consumer notes related operations
    """

    def add_notes(self, id, notes):
        """
        Adds notes (key-value information) to a consumer.

        @param id: unique identifier for the consumer
        @type  id: str

        @param notes: notes to be added to the existing notes of the consumer
        @type  notes: dict

        @raises MissingResource: if the given consumer does not exist
        @raises InvalidValue: if any of the fields is unacceptable
        """

        consumer = Consumer.get_collection().find_one({'id' : id})
        if consumer is None:
            raise MissingResource(id)

        if not isinstance(notes, dict):
            raise InvalidValue(notes)
        
        # Add notes
        existing_notes = consumer['notes']
        for key in notes.keys():
            if key in existing_notes.keys():
                raise InvalidValue(key)
            
        # To do - Find conflicting consumergroup notes, after we add support for consumergroups in V2
        
        for key, value in notes.items():
            existing_notes[key] = value
        consumer['notes'] = existing_notes
        Consumer.get_collection().save(consumer, safe=True)


    def remove_notes(self, id, notes):
        """
        Removes notes (key-value information) from a consumer.

        @param id: unique identifier for the consumer
        @type  id: str

        @param notes: notes to be removed from the existing notes of the consumer
        @type  notes: dict

        @raises MissingResource: if the given consumer does not exist
        @raises InvalidValue: if any of the fields is unacceptable
        """

        consumer = Consumer.get_collection().find_one({'id' : id})
        if consumer is None:
            raise MissingResource(id)

        if not isinstance(notes, dict):
            raise InvalidValue(notes)
        
        # Remove notes
        existing_notes = consumer['notes']
        for key in notes.keys():
            if key not in existing_notes.keys():
                raise InvalidValue()
            
        for key in notes.keys():
            del existing_notes[key]
        consumer['notes'] = existing_notes
        Consumer.get_collection().save(consumer, safe=True)


    def update_notes(self, id, notes):
        """
        Updates notes (key-value information) of a consumer.

        @param id: unique identifier for the consumer
        @type  id: str

        @param notes: notes to be updated
        @type  notes: dict

        @raises MissingResource: if the given consumer does not exist
        @raises InvalidValue: if any of the fields is unacceptable
        """

        consumer = Consumer.get_collection().find_one({'id' : id})
        if consumer is None:
            raise MissingResource(id)

        if not isinstance(notes, dict):
            raise InvalidValue(notes)
            
        # To do - Find conflicting consumergroup notes, after we add support for consumergroups in V2
        existing_notes = consumer['notes']
        for key, value in notes.items():
            existing_notes[key] = value
        consumer['notes'] = existing_notes
        Consumer.get_collection().save(consumer, safe=True)
        
    def get_notes(self, id):
        """
        Get notes (key-value information) of a consumer.

        @param id: unique identifier for the consumer
        @type  id: str
        """

        consumer = Consumer.get_collection().find_one({'id' : id})
        if consumer is None:
            raise MissingResource(id)

        return consumer['notes']
