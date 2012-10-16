# Copyright (c) 2010 Red Hat, Inc.
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
from pulp.server.db.model.migration_tracker import MigrationTracker


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


def get_current_package_version(migration_package):
    """
    Returns an integer that represents the migration version that the database is currently at. None
    means that the migration package has never been run before.
    """
    migration_version_collection = MigrationTracker.get_collection()
    migration_tracker = migration_version_collection.find_one({'id': migration_package.__name__})
    if migration_tracker is not None:
        migration_version = migration_tracker['version']
    else:
        migration_version = None
    return migration_version


def get_migration_packages():
    """
    This method finds all Python packages in pulp.server.db.migrations. It then sorts them
    alphabetically by name, and then prepends the pulp.server.db.platform pacage to the list.
    """
    migration_package_names = ['%s.%s'%(migrations.__name__, name) for \
                               module_loader, name, ispkg in \
                               pkgutil.iter_modules([os.path.dirname(migrations.__file__)])]
    migration_packages = [_get_python_module(migration_package_name) for \
                          migration_package_name in migration_package_names]
    print 'These aren\'t properly sorted yet.'
    return migration_packages


def get_migrations(migration_package):
    """
    Finds all available migration modules for the given typedef, adds a version attribute to them
    based on the number found at the beginning of their name, and then sorts by the version.

    :param typedef: The typedef in question
    :type typedef:  BSON object
    :returns:       A list of the migration modules for the typedef, sorted by version.
    :rtype:         L{Python modules}
    """
    module_names = [name for _, name, _ in \
                    pkgutil.iter_modules([os.path.dirname(migration_package.__file__)])]
    migration_modules = [_get_python_module('%s.%s'%(migration_package.__name__, module_name)) \
                         for module_name in module_names]
    for module in migration_modules:
        module.version = _get_migration_module_version(module)
    migration_modules = sorted(migration_modules,
                               cmp=lambda x,y: cmp(x.version, y.version))
    return migration_modules


def _get_migration_module_version(module):
    migration_module_name = module.__name__.split('.')[-1]
    version = int(re.match(r'(?P<version>\d+)_.*', migration_module_name).groupdict()['version'])
    return version


def _get_python_module(module_string):
    """
    The __import__ method returns the top level module when asked for a module with the dotted
    notation. For example, __import__('a.b.c') will return a, not c. This is fine, but we could use
    something that returns c for our migration discovery code. That's what this does.
    """
    module = __import__(module_string)
    parts_to_import = module_string.split('.')
    parts_to_import.pop(0)
    for part in parts_to_import:
        module = getattr(module, part)
    return module


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
