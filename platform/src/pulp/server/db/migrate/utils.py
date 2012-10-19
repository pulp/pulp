# Copyright (c) 2010-2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os
import pkgutil
import re

from pulp.server.db import migrations
from pulp.server.managers.migration_tracker import MigrationTrackerManager
import pulp.server.db.migrations.platform


class MigrationModule(object):
    """
    This is a wrapper around the real migration module. It allows us to add a version attribute to
    the module without interfering with the module's namespace, and it also natively sorts by
    migration version. It has a reference to the module's migrate() function as its migrate
    attribute.
    """
    def __init__(self, python_module_name):
        """
        Initialize a MigrationModule to represent the module passed in by python_module_name.

        :param python_module_name: The full python module name in dotted notation.
        :type  python_module_name: string
        """
        self._module = _import_all_the_way(python_module_name)
        self.version = self._get_version()
        self.migrate = self._module.migrate

    def _get_version(self):
        """
        Parse the module's name with a regex to determine the version of the module. The module is
        expected to be named something along the lines of ####<name>.py. We don't care how many
        digits are used to represent the number, but we do expect it to be the beginning of the
        name, and we do expect a trailing underscore.

        :returns:   The version of the module
        :rtype:     int
        """
        migration_module_name = self._module.__name__.split('.')[-1]
        version = int(re.match(r'^(?P<version>\d+).*',
                      migration_module_name).groupdict()['version'])
        return version

    def __cmp__(self, other_module):
        """
        This is used to get MigrationModules to sort by their version.

        :returns:   A negative value if self's version is less that other's, 0 if they are equal,
                    and a positive value if self's version is greater than other's.
        """
        return cmp(self.version, other_module.version)


class MigrationPackage(object):
    """
    A wrapper around the migration packages found in pulp.server.db.migrations. Has methods to
    retrieve information about the migrations that are found there, and to apply the migrations.
    """
    def __init__(self, python_package_name):
        """
        Initialize the MigrationPackage to represent the Python migration package passed in.

        :param python_package_name: The name of the Python package this object should represent, in
                                    dotted notation.
        :type  python_package_name: string
        """
        self._package = _import_all_the_way(python_package_name)
        migration_tracker_manager = MigrationTrackerManager()
        # This is an object representation of the DB object that keeps track of the migration
        # version that has been applied
        self._migration_tracker = migration_tracker_manager.get_or_create(
            name=self._package.__name__,
            defaults={'version': self.latest_available_version})

    def apply_migration(self, migration):
        """
        Apply the migration that is passed in, and update the DB to note the new version that this
        migration represents.

        :param migration: The migration to apply
        :type  migration: MigrationModule
        """
        migration.migrate()
        self._migration_tracker.version = migration.version
        self._migration_tracker.save()

    @property
    def available_versions(self):
        """
        Return a list of the migration versions that are available in this migration package.

        :rtype: L{int}
        """
        migrations = self.migrations
        versions = [migration.version for migration in migrations]
        return versions

    @property
    def current_version(self):
        """
        An integer that represents the migration version that the database is currently at.
        None means that the migration package has never been run before.

        :rtype: int
        """
        return self._migration_tracker.version

    @property
    def latest_available_version(self):
        """
        Return the version of the highest migration found in this package.

        :rtype: int
        """
        # If there aren't any versions available because this package is empty, we should return 0.
        # This means that we need to require migration writers not to create versions that are less
        # than 1.
        return self.available_versions[-1] if self.available_versions else 0

    @property
    def migrations(self):
        """
        Finds all available migration modules for the MigrationPackage,
        and then sorts by the version.

        :rtype:         L{MigrationModule}
        """
        # Generate a list of the names of the modules found inside this package
        module_names = [name for module_loader, name, ispkg in
                        pkgutil.iter_modules([os.path.dirname(self._package.__file__)])]
        migration_modules = [MigrationModule('%s.%s'%(self.name, module_name))
                             for module_name in module_names]
        migration_modules.sort()
        return migration_modules

    @property
    def name(self):
        """
        Returns the name of the Python package that this MigrationPackage represents.

        :rtype: str
        """
        return self._package.__name__

    @property
    def unapplied_migrations(self):
        """
        Return a list of MigrationModules in this package that have not been applied yet.

        :rtype: L{MigrationModule}
        """
        return [migration for migration in self.migrations \
                if migration.version > self.current_version]

    def __cmp__(self, other_package):
        """
        This method returns a negative value if self.name < other_package.name, 0 if they are
        equal, and a positive value if self.name > other_package.name. There is an exception to
        this sorting rule, in that if self._package is pulp.server.db.migrations.platform, this
        method will always return -1.

        :rtype: int
        """
        if self._package is pulp.server.db.migrations.platform:
            return -1
        return cmp(self.name, other_package.name)

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)


def add_field_with_default_value(objectdb, field, default=None):
    """
    Add a new field to all instances of a model in the passed in collection and
    set the value of the field to the default.
    @type objectdb: pymongo.collection.Collection instance
    @param objectdb: collection of models to add field to
    @type field: str
    @param field: name of the field to add
    @type default: any
    @param default: default value to set new field to
    """
    for model in objectdb.find():
        if field not in model:
            model[field] = default
            objectdb.save(model, safe=True)


def change_field_type_with_default_value(objectdb, field, new_type, default_value):
    """
    Change type of the field for all instances of a model in the passed in collection and
    set the value of the field to the default_value.
    @type objectdb: pymongo.collection.Collection instance
    @param objectdb: collection of models to change field type
    @type field: str
    @param field: name of the field to update type
    @type new_type: str
    @param new_type: new type of the field
    @type default_value: any
    @param default_value: default value to set the field to
    """
    for model in objectdb.find():
            if not isinstance(model[field], new_type):
                model[field] = default_value
                objectdb.save(model, safe=True)


def add_field_with_calculated_value(objectdb, field, callback=lambda m: None):
    """
    Add a new field to all instances of a model in the passed in collection and
    set the value of the field to the return value of the callback that takes
    the model as an argument.
    @type objectdb: pymongo.collection.Collection instance
    @param objectdb: collection of models to add field to
    @type field: str
    @param field: name of the field to add
    @type callback: python callable
    @param callback: callable that takes the model as an argument and returns
                     the value for the new field
    """
    for model in objectdb.find():
        if field not in model:
            model[field] = callback(model)
            objectdb.save(model, safe=True)


def delete_field(objectdb, field):
    """
    Delete a field from all model instances in a collection.
    @type objectdb: pymongo.collection.Collection instance
    @param objectdb: collection of models to delete field from
    @type field: str
    @param field: name of the field to delete
    """
    for model in objectdb.find():
        if field not in model:
            continue
        del model[field]
        objectdb.save(model, safe=True)


def get_migration_packages():
    """
    This method finds and returns all Python packages in pulp.server.db.migrations. It sorts them
    alphabetically by name, except that pulp.server.db.platform unconditionally sorts to the front
    of the list.

    :rtype: L{MigrationPackage}
    """
    migration_package_names = ['%s.%s'%(migrations.__name__, name) for
                               module_loader, name, ispkg in
                               pkgutil.iter_modules([os.path.dirname(migrations.__file__)])]
    migration_packages = [MigrationPackage(migration_package_name) for
                          migration_package_name in migration_package_names]
    migration_packages.sort()
    return migration_packages


def migrate_field(objectdb,
                  from_field,
                  to_field,
                  callback=lambda v: v,
                  delete_from=False):
    """
    Migrate data from one field to another within the same model for all
    instance in the passed in collection.
    @type objectdb: pymongo.collection.Collection instance
    @param objectdb: collection of models to migrate fields in
    @type from_field: str
    @param from_field: name of the field to migrate data from
    @type to_field: str
    @param to_field: name of the field to migrate data to
    @type callback: python callable
    @param callback: callable that takes the from_field value as an argument
                     and returns the to_field value
    @type delete_from: bool
    @param delete_from: when set to True, the from_field is deleted from the
                        model, otherwise it is left
    """
    for model in objectdb.find():
        model[to_field] = callback(model[from_field])
        if delete_from:
            del model[from_field]
        objectdb.save(model, safe=True)


def _import_all_the_way(module_string):
    """
    The __import__ method returns the top level module when asked for a module with the dotted
    notation. For example, __import__('a.b.c') will return a, not c. This is fine, but we could
    use something that returns c for our migration discovery code. That's what this does.

    :param module_string: A dot notation of the Python module to be imported and returned
    :type  module_string: str
    :rtype:               Python package or module
    """
    module = __import__(module_string)
    parts_to_import = module_string.split('.')
    parts_to_import.pop(0)
    for part in parts_to_import:
        module = getattr(module, part)
    return module
