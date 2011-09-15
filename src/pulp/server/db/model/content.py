# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from pulp.server.db.model.base import Model

# -- classes -----------------------------------------------------------------

class ContentType(Model):
    """
    Represents a content type supported by the Pulp server. This is purely the
    metadata about the type and will not contain any instances of content of
    the type.

    @ivar id: uniquely identifies the type
    @type id: str

    @ivar display_name: user-friendly name of the content type
    @type display_name: str

    @ivar description: user-friendly explanation of the content type's purpose
    @type description: str

    @ivar unique_indexes: list of unique indexes created for the type's collection
    @type unique_indexes: list of str

    @ivar search_indexes: list of additional indexes used to optimize search
                          within this type
    @type search_indexes: list of str

    @ivar child_types: list of IDs of types that may be referenced from units
                       of this type
    @type child_types: list of str
    """

    collection_name = 'content_types'
    unique_indices = ('id',)

    def __init__(self, id, display_name, description, unique_indexes, search_indexes, child_types):
        self.id = id
        self._id = id

        self.display_name = display_name
        self.description = description
        
        self.unique_indexes = unique_indexes
        self.search_indexes = search_indexes

        self.child_types = child_types