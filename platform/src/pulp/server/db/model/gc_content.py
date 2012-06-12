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

    @ivar unit_key: list of fields that compromise the unique key for units of the type
    @type unit_key: list of str

    @ivar search_indexes: list of additional indexes used to optimize search
                          within this type
    @type search_indexes: list of str

    @ivar referenced_types: list of IDs of types that may be referenced from units
                            of this type
    @type referenced_types: list of str
    """

    collection_name = 'content_types'
    unique_indices = ('id',)

    def __init__(self, id, display_name, description, unit_key, search_indexes, referenced_types):
        super(ContentType, self).__init__()

        self.id = id

        self.display_name = display_name
        self.description = description
        
        self.unit_key = unit_key
        self.search_indexes = search_indexes

        self.referenced_types = referenced_types