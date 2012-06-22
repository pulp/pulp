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

from pulp.server.db.model.auth import User, Role, Permission
from pulp.server.db.model.consumer import Bind, Consumer, ConsumerHistoryEvent
from pulp.server.db.model.content import ContentType
from pulp.server.db.model.event import EventListener
from pulp.server.db.model.repository import Repo, RepoContentUnit, RepoDistributor, RepoImporter, RepoPublishResult, RepoSyncResult
from pulp.server.db.model.base import Model

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


def _validate_bind():
    objectdb = Bind.get_collection()
    reference = Bind('', '', '')
    return _validate_model(Bind.__name__, objectdb, reference)

def _validate_consumer():
    objectdb = Consumer.get_collection()
    reference = Consumer('', '')
    return _validate_model(Consumer.__name__, objectdb, reference)

def _validate_consumer_history():
    objectdb = ConsumerHistoryEvent.get_collection()
    reference = ConsumerHistoryEvent('', '', '', {})
    return _validate_model(ConsumerHistoryEvent.__name__, objectdb, reference)

def _validate_content_type():
    objectdb = ContentType.get_collection()
    reference = ContentType('', '', '', [], [], [])
    return _validate_model(ConsumerHistoryEvent.__name__, objectdb, reference)

def _validate_event_listener():
    objectdb = EventListener.get_collection()
    reference = EventListener('', {}, [])
    return _validate_model(EventListener.__name__, objectdb, reference)

def _validate_permission():
    """
    Validate the Permission model
    @rtype: int
    @return: number of errors found during validation
    """
    objectdb = Permission.get_collection()
    reference = Permission(u'')
    _base_id(reference)
    return _validate_model(Permission.__name__, objectdb, reference)

def _validate_repo():
    objectdb = Repo.get_collection()
    reference = Repo('', '')
    return _validate_model(Repo.__name__, objectdb, reference)

def _validate_repo_content_unit():
    objectdb = RepoContentUnit.get_collection()
    reference = RepoContentUnit('', '', '', '', '')
    return _validate_model(RepoContentUnit.__name__, objectdb, reference)

def _validate_repo_distributor():
    objectdb = RepoDistributor.get_collection()
    reference = RepoDistributor('', '', '', {}, True)
    return _validate_model(RepoDistributor.__name__, objectdb, reference)

def _validate_repo_importer():
    objectdb = RepoImporter.get_collection()
    reference = RepoImporter('', '', '', {})
    return _validate_model(RepoImporter.__name__, objectdb, reference)

def _validate_repo_publish_result():
    objectdb = RepoPublishResult.get_collection()
    reference = RepoPublishResult('', '', '', '', '', '')
    return _validate_model(RepoPublishResult.__name__, objectdb, reference)

def _validate_repo_sync_result():
    objectdb = RepoSyncResult.get_collection()
    reference = RepoSyncResult('', '', '', '', '', '')
    return _validate_model(RepoSyncResult.__name__, objectdb, reference)

def _validate_role():
    """
    Validate the Role model
    @rtype: int
    @return: number of errors found during validation
    """
    objectdb = Role.get_collection()
    reference = Role(u'')
    return _validate_model(Role.__name__, objectdb, reference)


def _validate_user():
    """
    Validate the User model
    @rtype: int
    @return: number of errors found during validation
    """
    objectdb = User.get_collection()
    reference = User(u'', u'', None, None)
    return _validate_model(User.__name__, objectdb, reference)

# validation api --------------------------------------------------------------

def validate():
    """
    Perform data model validation for all collections in the current data model
    @rtype: int
    @return: number of errors found during validation
    """
    num_errors = 0
    num_errors += _validate_data_model_version()
    num_errors += _validate_bind()
    num_errors += _validate_consumer()
    num_errors += _validate_consumer_history()
    num_errors += _validate_content_type()
    num_errors += _validate_event_listener()
    num_errors += _validate_permission()
    num_errors += _validate_repo()
    num_errors += _validate_repo_content_unit()
    num_errors += _validate_repo_distributor()
    num_errors += _validate_repo_importer()
    num_errors += _validate_repo_publish_result()
    num_errors += _validate_repo_sync_result()
    num_errors += _validate_role()
    num_errors += _validate_user()
    return num_errors
