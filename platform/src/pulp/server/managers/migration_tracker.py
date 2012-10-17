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

class MigrationTrackerManager(object):
    def __init__(self):
        self._collection = MigrationTracker.get_collection()

    def create(self, id, version):
        new_mt = MigrationTracker(id=id, version=version)
        new_mt.save()
        return new_mt

    def get(self, id):
        migration_tracker = self._collection.find_one({'id': id})
        if migration_tracker is not None:
            migration_tracker = MigrationTracker(id=migration_tracker['id'],
                                                 version=migration_tracker['version'])
            return migration_tracker
        raise DoesNotExist('MigrationTracker with id %s does not exist.')

    def get_or_create(self, id, defaults=None):
        try:
            migration_tracker = self.get(id)
        except DoesNotExist:
            if defaults is None:
                defaults = {}
            version = defaults.get('version', None)
            migration_tracker = self.create(id, version=version)
        return migration_tracker
