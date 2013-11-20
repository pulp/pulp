# Copyright (c) 2012 Red Hat, Inc.
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


class MigrationTracker(Model):
    """
    This is used to track state about our migrations package. There will be one object for each
    migration package in pulp.server.db.migrations, and we will track which migration version each
    of those packages have been advanced to.

    :ivar name:    Uniquely identifies the package, and is the name of the package
    :type name:    str
    :ivar version: The version that the migration package is currently at
    :type version: int
    """

    collection_name = 'migration_trackers'
    unique_indices = ('name',)

    def __init__(self, name, version):
        """
        Initialize the MigrationTracker with name and version.

        :param name:    The name is used to store the name of the migration package this object is
                        tracking
        :type  name:    str
        :param version: The version we want to set for the MigrationTracker
        :type  version: int
        """
        super(MigrationTracker, self).__init__()

        self.name = name
        self.version = version

    def save(self):
        """
        Save any changes made to this MigrationTracker to the database. If it doesn't exist in the
        database already, insert a new record to represent it.
        """
        self.get_collection().update({'name': self.name},
                                     {'name': self.name, 'version': self.version},
                                     upsert=True, safe=True)
