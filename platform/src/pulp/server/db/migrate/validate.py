# -*- coding: utf-8 -*-

# Copyright © 2010-2011 Red Hat, Inc.
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
import datetime
from pulp.common import dateutils

from pulp.server.db.model.audit import Event
from pulp.server.db.model.auth import User, Role, Permission
from pulp.server.db.model.base import Model
from pulp.server.db.model.cds import CDS, CDSHistoryEvent, CDSRepoRoundRobin
from pulp.server.db.model.resource import (Consumer, ConsumerGroup,
    ConsumerHistoryEvent, Errata, Package, Distribution, File, Repo)


from pulp.server.db import model
from pulp.server.db import version


_log = getLogger('pulp')

# reference utilities ---------------------------------------------------------

def _base_id(reference):
    # XXX this is a hack because I've no idea what the type of pymongo's
    # default _id field is
    reference._id = reference.id = None


def _unicodify_reference(reference):
    if not isinstance(reference, Model):
        return reference
    for key, value in reference.items():
        if isinstance(value, str):
            reference[key] = unicode(value)
    return reference

# general model validation ----------------------------------------------------

def _validate_model(model_name, objectdb, reference, values={}):
    """
    Perform a general validation of field presence and field value type for a
    given collection, and model reference
    @type model_name: str
    @param model_name: name of the model being validated
    @type objectdb: pymongo.collection.Collection instance
    @param objectdb: model collection to validate
    @type reference: L{pulp.server.db.model.Base} instance
    @param reference: reference data model instance for comparisons
    @type values: dict
    @param values: a dictionar of valid values for fields in the document
                   {field: [list of valid values],}
    @rtype: int
    @return: number of errors found during validation
    """
    num_errors = 0
    # convert all the str fields to unicode as all strings coming out of our
    # database have been converted to unicode
    reference = _unicodify_reference(reference)
    for model in objectdb.find():
        for field, value in reference.items():
            vtype = type(value)
            # a default value of None really can't be automatically validated,
            # and should be validated in the individual validation method
            if field in model and (value is None or
                                   isinstance(model[field], vtype)):
                if field not in values:
                    continue
                elif value in values[field]:
                    continue
            num_errors += 1
            error_prefix = 'model validation failure in %s for model %s:' % \
                    (model_name, str(model['_id']))
            if field not in model:
                _log.error(error_prefix + ' field %s is not present' % field)
            elif not isinstance(model[field], vtype):
                error_msg = error_prefix + ' field %s is %s not %s'
                _log.error(error_msg % (field, type(model[field]), vtype))
            else:
                error_msg = error_prefix + ' field %s value is not: %s'
                _log.error(error_msg % (field, ','.join(values[field])))
    return num_errors

# individual model validation -------------------------------------------------

def _validate_consumer():
    """
    Validate the Consumer model
    @rtype: int
    @return: number of errors found during validation
    """
    objectdb = Consumer.get_collection()
    reference = model.Consumer(u'', None)
    return _validate_model(model.Consumer.__name__, objectdb, reference)


def _validate_consumer_group():
    """
    Validate the ConsumerGroup model
    @rtype: int
    @return: number of errors found during validation
    """
    objectdb = ConsumerGroup.get_collection()
    reference = model.ConsumerGroup(u'')
    return _validate_model(model.ConsumerGroup.__name__, objectdb, reference)


def _validate_consumer_history_event():
    """
    Validate the ConsumerHistroyEvent model
    @rtype: int
    @return: number of errors found during validation
    """
    objectdb = ConsumerHistoryEvent.get_collection()
    reference = model.ConsumerHistoryEvent(u'', u'', u'', None)
    _base_id(reference)
    return _validate_model(model.ConsumerHistoryEvent.__name__,
                           objectdb,
                           reference)


def _validate_data_model_version():
    """
    Validate the DataModelVersion model
    @rtype: int
    @return: number of errors found during validation
    """
    objectdb = version._version_db
    reference = version.DataModelVersion(0)
    return _validate_model(version.DataModelVersion.__name__,
                           objectdb,
                           reference)


def _validate_errata():
    """
    Validate the Errata model
    @rtype: int
    @return: number of errors found during validation
    """
    objectdb = Errata.get_collection()
    reference = model.Errata(u'', u'', None, u'', u'', u'')
    return _validate_model(model.Errata.__name__, objectdb, reference)


def _validate_event():
    """
    Validate the Event model
    (used for auditing)
    @rtype: int
    @return: number of errors found during validation
    """
    objectdb = Event.get_collection()
    reference = model.Event(u'', u'')
    _base_id(reference)
    return _validate_model(model.Event.__name__, objectdb, reference)


def _validate_package():
    """
    Validate the Package model
    @rtype: int
    @return: number of errors found during validation
    """
    objectdb = Package.get_collection()
    reference = model.Package(u'', u'', u'', u'', u'', u'', u'', u'', u'')
    _base_id(reference)
    return _validate_model(model.Package.__name__, objectdb, reference)


def _validate_package_group():
    """
    Validate the PackageGroup model
    @rtype: int
    @return: number of errors found during validation
    """
    num_errors = 0
    objectdb = Repo.get_collection()
    reference = _unicodify_reference(model.PackageGroup(u'', u'', u''))
    for r in objectdb.find({'packagegroups': {'$gt': 0}}):
        for pg in r['packagegroups'].values():
            for field, value in reference.items():
                vtype = value(type)
                if field in pg and (value is None or isinstance(pg[field], vtype)):
                    continue
                num_errors += 1
                error_prefix = 'model validation failure in PackageGroup for Repo %s, PackageGroup %s:' % \
                        (str(r['_id']), str(pg['_id']))
                if field not in pg:
                    _log.error(error_prefix + ' field %s is not present' %
                               field)
                else:
                    _log.error(error_prefix + ' field %s is not a %s' %
                               (field, vtype))
    return num_errors


def _validate_package_group_category():
    """
    Validate the PackageGroupCategory model
    @rtype: int
    @return: number of errors found during validation
    """
    num_errors = 0
    objectdb = Repo.get_collection()
    reference = _unicodify_reference(model.PackageGroupCategory(u'', u'', u''))
    for r in objectdb.find({'packagegroupcategories': {'$gt': 0}}):
        for pgc in r['packagegroupcategories'].values():
            for field, value in reference.items():
                vtype = value(type)
                if field in pgc and (value is None or
                                     isinstance(pgc[field], vtype)):
                    continue
                num_errors += 1
                error_prefix = 'model validation failure in PackageGroupCategory for Repo %s, PackageGroup %s:' % \
                        (str(r['_id']), str(pgc['_id']))
                if field not in pgc:
                    _log.error(error_prefix + ' field %s is not present' %
                               field)
                else:
                    _log.error(error_prefix + ' field %s is not a %s' %
                               (field, vtype))
    return num_errors


def _validate_permission():
    """
    Validate the Permission model
    @rtype: int
    @return: number of errors found during validation
    """
    objectdb = Permission.get_collection()
    reference = model.Permission(u'')
    _base_id(reference)
    return _validate_model(model.Permission.__name__, objectdb, reference)


def _validate_repo():
    """
    Validate the Repo model
    @rtype: int
    @return: number of errors found during validation
    """
    objectdb = Repo.get_collection()
    reference = model.Repo(u'', u'', u'', u'')
    return _validate_model(model.Repo.__name__, objectdb, reference)


def _validate_repo_source():
    """
    Validate the RepoSource model
    @rtype: int
    @return: number of errors found during validation
    """
    num_errors = 0
    objectdb = Repo.get_collection()
    reference = _unicodify_reference(
                model.RepoSource(u'http://reference.org/reference_repo/'))
    for r in objectdb.find({'source': {'$ne': None}}):
        source = r['source']
        for field, value in reference.items():
            vtype = type(value)
            if field in source and isinstance(source[field], vtype):
                continue
            num_errors += 1
            error_prefix = 'model validation failure in RepoSource for Repo %s:' % \
                    str(r['_id'])
            if field not in source:
                _log.error(error_prefix + ' field %s is not present' % field)
            else:
                _log.error(error_prefix + ' field %s is not a %s' %
                           (field, vtype))
    return num_errors


def _validate_role():
    """
    Validate the Role model
    @rtype: int
    @return: number of errors found during validation
    """
    objectdb = Role.get_collection()
    reference = model.Role(u'')
    return _validate_model(model.Role.__name__, objectdb, reference)


def _validate_user():
    """
    Validate the User model
    @rtype: int
    @return: number of errors found during validation
    """
    objectdb = User.get_collection()
    reference = model.User(u'', u'', None, None)
    return _validate_model(model.User.__name__, objectdb, reference)


def _validate_file():
    """
    Validate the File model
    @rtype: int
    @return: number of errors found during validation
    """
    objectdb = File.get_collection()
    reference = model.File(u'', u'', u'', 0, None)
    _base_id(reference)
    return _validate_model(model.File.__name__, objectdb, reference)


def _validate_distribution():
    """
    Validate the Distribution model
    @rtype: int
    @return: number of errors found during validation
    """
    objectdb = Distribution.get_collection()
    reference = model.Distribution(u'', u'', u'', None, None, None, None, [], None)
    _base_id(reference)
    return _validate_model(model.Distribution.__name__, objectdb, reference)


def _validate_cds():
    '''
    Validates the CDS model.
    '''
    objectdb = CDS.get_collection()
    reference = CDS(u'', u'')
    return _validate_model(CDS.__name__, objectdb, reference)

def _validate_cds_history():
    '''
    Validates the CDS history event model.
    '''
    objectdb = CDSHistoryEvent.get_collection()
    reference = CDSHistoryEvent(u'', u'', u'')
    return _validate_model(CDSHistoryEvent.__name__, objectdb, reference)


def _validate_cds_round_robin():
    '''
    Validates the round robin algorithm collection.
    '''
    objectdb = CDSRepoRoundRobin.get_collection()
    reference = CDSRepoRoundRobin(u'', [])
    return _validate_model(CDSRepoRoundRobin.__name__, objectdb, reference)


# validation api --------------------------------------------------------------

def validate():
    """
    Perform data model validation for all collections in the current data model
    @rtype: int
    @return: number of errors found during validation
    """
    num_errors = 0
    num_errors += _validate_consumer()
    num_errors += _validate_consumer_group()
    num_errors += _validate_consumer_history_event()
    num_errors += _validate_data_model_version()
    num_errors += _validate_errata()
    num_errors += _validate_event()
    num_errors += _validate_package()
    num_errors += _validate_package_group()
    num_errors += _validate_package_group_category()
    num_errors += _validate_repo()
    num_errors += _validate_permission()
    num_errors += _validate_repo_source()
    num_errors += _validate_role()
    num_errors += _validate_user()
    num_errors += _validate_file()
    num_errors += _validate_distribution()
    num_errors += _validate_cds()
    num_errors += _validate_cds_history()
    num_errors += _validate_cds_round_robin()
    return num_errors
