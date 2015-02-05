from pulp.server.managers import factory as managers


class CatalogerConduit(object):
    """
    Provides access to pulp platform API.
    """

    def __init__(self, source_id, expires):
        """
        :param source_id: The content source ID.
        :type source_id: str
        :param expires: The content expiration in seconds.
        :type expires: int
        :return:
        """
        self.source_id = source_id
        self.expires = expires
        self.added_count = 0
        self.deleted_count = 0

    def add_entry(self, type_id, unit_key, url):
        """
        Add an entry to the content catalog.
        :param type_id: The content unit type ID.
        :type type_id: str
        :param unit_key: The content unit key.
        :type unit_key: dict
        :param url: The URL used to download content associated with the unit.
        :type url: str
        """
        manager = managers.content_catalog_manager()
        manager.add_entry(self.source_id, self.expires, type_id, unit_key, url)
        self.added_count += 1

    def delete_entry(self, type_id, unit_key):
        """
        Delete an entry from the content catalog.
        :param type_id: The content unit type ID.
        :type type_id: str
        :param unit_key: The content unit key.
        :type unit_key: dict
        """
        manager = managers.content_catalog_manager()
        manager.delete_entry(self.source_id, type_id, unit_key)
        self.deleted_count += 1

    def reset(self):
        """
        Reset statistics.
        """
        self.added_count = 0
        self.deleted_count = 0
