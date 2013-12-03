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

import json

from hashlib import sha256
from datetime import datetime, timedelta

from pulp.common import dateutils
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


class ContentCatalog(Model):
    """
    Represents a catalog of available content provided by content sources.
    Things to know about the catalog:
     - Entries are contributed by content sources.
     - Each entry contains an expiration timestamp.  Entries are permitted
       to remain in the catalog until they expire (plus an optional grace period).
     - The locator is a hashed json encoding of the type_id and unit_key.  It is
       used for fast indexing and searching since the unit_key is arbitrary.
     - The catalog may be refreshed concurrently.
     - The catalog provides best effort read consistency by:
       - lazily purging expired entries.
       - supporting find() operations on a catalog containing multiple entries
         matching the same locator.  In these cases, only the newest entry is
         included for each source in the result set.
    :ivar source_id: The ID of the contributing content source.
    :type source_id: str
    :ivar expires: The expiration UTC timestamp.
    :type expires: int
    :ivar type_id: The unit type ID.
    :type type_id: str
    :ivar unit_key: The unit key.
    :type unit_key: dict
    :ivar locator: The hashed json encoding of the type_id and unit_key used for searching.
    :type locator: str
    :ivar url: The URL used to download the file associated with the unit.
    :type url: str
    """

    collection_name = 'content_catalog'
    search_indices = ('source_id', 'locator')
    unique_indices = ()

    @staticmethod
    def get_locator(type_id, unit_key):
        """
        Get the locator for the specified type_id and unit_key.
        The locator is the SHA256 of the json encoding of the type_id and unit_key.
        :param type_id: A content unit's type ID.
        :type type_id: str
        :param unit_key: A content unit's key.
        :type unit_key: dict
        :return: The calculated locator string.
        :rtype: str
        """
        h = sha256()
        s = json.dumps((type_id, unit_key), separators=(',', ':'), sort_keys=True)
        h.update(s)
        return h.hexdigest()

    @staticmethod
    def get_expiration(duration):
        """
        Get an expiration timestamp using the specified duration in seconds.
        :param duration: The duration in seconds.
        :type duration: int
        :return: The timestamp.
        :rtype: int
        """
        now = datetime.now(dateutils.utc_tz())
        dt = now + timedelta(seconds=duration)
        return dateutils.datetime_to_utc_timestamp(dt)

    def __init__(self, source_id, expiration, type_id, unit_key, url):
        """
        :param source_id: The ID of the contributing content source.
        :type source_id: str
        :param expiration: The expiration (duration in seconds).
        :type expiration: int
        :param type_id: A content unit's type ID.
        :type type_id: str
        :param unit_key: A content unit's key.
        :type unit_key: dict
        :param url: The URL used to download the file associated with the unit.
        :type url: str
        """
        Model.__init__(self)
        self.source_id = source_id
        self.expiration = self.get_expiration(expiration)
        self.type_id = type_id
        self.unit_key = unit_key
        self.locator = self.get_locator(type_id, unit_key)
        self.url = url
