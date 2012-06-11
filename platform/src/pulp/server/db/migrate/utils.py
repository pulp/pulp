# -*- coding: utf-8 -*-

# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


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
