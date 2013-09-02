# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

from pulp.server.db.model.migration_tracker import MigrationTracker


class DoesNotExist(Exception):
    """
    This Exception is raised when the manager is asked to retrieve a MigrationTracker that is not
    found in the database.
    """
    pass


class MigrationTrackerManager(object):
    """
    A manager that is used to create or retrieve MigrationTracker objects from the database.
    """
    def __init__(self):
        self._collection = MigrationTracker.get_collection()

    def create(self, name, version):
        """
        Create and return a MigrationTracker with specified name and version.

        :param name:    The name of the package that the MigrationTracker is tracking.
        :type  name:    str
        :param version: The version we want to store on the new MigrationTracker.
        :type  version: int
        :rtype:         pulp.server.db.model.migration_tracker.MigrationTracker
        """
        new_mt = MigrationTracker(name=name, version=version)
        new_mt.save()
        return new_mt

    def get(self, name):
        """
        Retrieve a MigrationTracker from the database by name.

        :param name: The name of the MigrationTracker that we wish to retrieve.
        :type  name: str
        :rtype:      pulp.server.db.model.migration_tracker.MigrationTracker
        """
        migration_tracker = self._collection.find_one({'name': name})
        if migration_tracker is not None:
            migration_tracker = MigrationTracker(name=migration_tracker['name'],
                                                 version=migration_tracker['version'])
            return migration_tracker
        raise DoesNotExist('MigrationTracker with id %s does not exist.')

    def get_or_create(self, name, defaults=None):
        """
        Try to retrieve a MigrationTracker with specified name from the database. If it exists,
        return it. If it doesn't exist, create a new one with specified name, and with the version
        attribute specified in a dictionary passed to defaults with one key, 'version'.

        :param name:     The name of the MigrationTracker to get or create
        :type  name:     str
        :param defaults: An optional dictionary with a single key, 'version'. This is used to set a
                         version on a new MigrationTracker, in the event that this method creates
                         one
        :type  defaults: dict
        :rtype:          pulp.server.db.model.migration_tracker.MigrationTracker
        """
        try:
            migration_tracker = self.get(name)
        except DoesNotExist:
            if defaults is None:
                defaults = {}
            version = defaults.get('version', None)
            migration_tracker = self.create(name, version=version)
        return migration_tracker
