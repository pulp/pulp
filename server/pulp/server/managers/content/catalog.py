# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from logging import getLogger

from pymongo import ASCENDING

from pulp.server.db.model.content import ContentCatalog


log = getLogger(__name__)


# The grace period in seconds.
# The grace_period defines how long an entry is permitted to remain
# in the catalog after it has expired.
GRACE_PERIOD = 3600  # 1 hour.


class ContentCatalogManager(object):
    """
    Manages the content unit catalog.
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
    """

    def add_entry(self, source_id, expires, type_id, unit_key, url):
        """
        Add an entry to the content catalog.
        :param source_id: A content source ID.
        :type source_id: str
        :param expires: The entry expiration in seconds.
        :type expires: int
        :param type_id: The unit type ID.
        :type type_id: str
        :param unit_key: The unit key.
        :type unit_key: dict
        :param url: The download URL.
        :type url: str
        """
        collection = ContentCatalog.get_collection()
        entry = ContentCatalog(source_id, expires, type_id, unit_key, url)
        collection.insert(entry, safe=True)

    def delete_entry(self, source_id, type_id, unit_key):
        """
        Delete an entry from the content catalog.
        :param source_id: A content source ID.
        :type source_id: str
        :param type_id: The unit type ID.
        :type type_id: str
        :param unit_key: The unit key.
        :type unit_key: dict
        """
        collection = ContentCatalog.get_collection()
        locator = ContentCatalog.get_locator(type_id, unit_key)
        query = {'source_id': source_id, 'locator': locator}
        collection.remove(query, safe=True)

    def purge(self, source_id):
        """
        Purge (delete) entries from the content catalog belonging
        to the specified content source by ID.
        :param source_id: A content source ID.
        :type source_id: str
        :return: The number of entries purged.
        :rtype: int
        """
        collection = ContentCatalog.get_collection()
        query = {'source_id': source_id}
        result = collection.remove(query, safe=True)
        return result['n']

    def purge_expired(self, grace_period=GRACE_PERIOD):
        """
        Purge (delete) expired entries from the content catalog belonging
        to the specified content source by ID.
        :param grace_period: The grace period in seconds.
            The grace_period defines how long an entry is permitted to remain
            in the catalog after it has expired.  The default is 1 hour.
        :type grace_period: int
        :return: The number of entries purged.
        :rtype: int
        """
        collection = ContentCatalog.get_collection()
        now = ContentCatalog.get_expiration(0)
        timestamp = now - grace_period
        query = {'expiration': {'$lt': timestamp}}
        result = collection.remove(query, safe=True)
        return result['n']

    def purge_orphans(self, valid_ids):
        """
        Purge orphan entries from the content catalog.
        Entries are orphaned when the content source to which they belong
        is no longer loaded.
        :param valid_ids: The list of valid (loaded) content source IDs.
        :type valid_ids: list
        :return: The number of entries purged.
        :rtype: int
        """
        purged = 0
        collection = ContentCatalog.get_collection()
        for source_id in collection.distinct('source_id'):
            if source_id not in valid_ids:
                purged += self.purge(source_id)
        return purged

    def find(self, type_id, unit_key):
        """
        Find entries in the content catalog using the specified unit type_id
        and unit_key.  The catalog may contain more than one entry matching the
        locator for a given content source.  In this case, only the newest entry
        for each source is included in the result set.
        :param type_id: The unit type ID.
        :type type_id: str
        :param unit_key: The unit key.
        :type unit_key: dict
        :return: A list of matching entries.
        :rtype: list
        """
        collection = ContentCatalog.get_collection()
        locator = ContentCatalog.get_locator(type_id, unit_key)
        query = {
            'locator': locator,
            'expiration': {'$gte': ContentCatalog.get_expiration(0)}
        }
        newest_by_source = {}
        for entry in collection.find(query, sort=[('_id', ASCENDING)]):
            newest_by_source[entry['source_id']] = entry
        return newest_by_source.values()

    def has_entries(self, source_id):
        """
        Get whether the specified content source has entries in the catalog.
        :param source_id: A content source ID.
        :type source_id: str
        :return: True if has entries.
        :rtype: bool
        """
        collection = ContentCatalog.get_collection()
        query = {
            'source_id': source_id,
            'expiration': {'$gte': ContentCatalog.get_expiration(0)}
        }
        cursor = collection.find(query)
        return cursor.count() > 0
