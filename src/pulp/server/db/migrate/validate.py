# -*- coding: utf-8 -*-

# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

from logging import getLogger

from pulp.server.api import (
    consumer_group, consumer_history, consumer, errata, package, repo, user)
from pulp.server.auditing import _objdb as auditing_objectdb
from pulp.server.db import model


_log = getLogger('pulp')

# general model validation ----------------------------------------------------

def _validate_model(model_name, objectdb, reference):
    """
    Perform a general validation of field presence and field value type for a
    given collection, and model reference
    @type model_name: str
    @param model_name: name of the model being validated
    @type objectdb: pymongo.collection.Collection instance
    @param objectdb: model collection to validate
    @type reference: L{pulp.server.db.model.Base} instance
    @param reference: reference data model instance for comparisons
    @rtype: int
    @return: number of errors found during validation
    """
    num_errors = 0
    for model in objectdb.find():
        for field, value in reference.items():
            vtype = type(value)
            # a default value of None really can't be automatically validated, 
            # should be validated in the individual validation method
            if field in model and (value is None or isinstance(model[field], vtype)):
                continue
            num_errors += 1
            if field not in model:
                _log.error('model validation failure in %s for model %s: field %s is not present' %
                           model_name, str(model['_id']), field)
            else:
                _log.error('model validation failure in %s for model %s: field %s is not a %s' %
                           model_name, str(model['_id']), field, vtype)
    return num_errors

# individual model validation -------------------------------------------------

def _validate_consumer():
    """
    Validate the Consumer model
    @rtype: int
    @return: number of errors found during validation
    """
    objectdb = consumer.ConsumerApi()._getcollection()
    reference = model.Consumer('', '')
    return _validate_model(model.Consumer.__name__, objectdb, reference)


def _validate_consumer_group():
    """
    Validate the ConsumerGroup model
    @rtype: int
    @return: number of errors found during validation
    """
    objectdb = consumer_group.ConsumerGroupApi()._getcollection()
    reference = model.ConsumerGroup('', '')
    return _validate_model(model.ConsumerGroup.__name__, objectdb, reference)


def _validate_consumer_history_event():
    """
    Validate the ConsumerHistroyEvent model
    @rtype: int
    @return: number of errors found during validation
    """
    objectdb = consumer_history.ConsumerHistoryApi()._getcollection()
    reference = model.ConsumerHistoryEvent('', '', '', '')
    return _validate_model(model.ConsumerHistoryEvent.__name__, objectdb, reference)


def _validate_errata():
    """
    Validate the Errata model
    @rtype: int
    @return: number of errors found during validation
    """
    objectdb = errata.ErrataApi()._getcollection()
    reference = model.Errata('', '', '', '', '', '')
    return _validate_model(model.Errata.__name__, objectdb, reference)


def _validate_event():
    """
    Validate the Event model
    (used for auditing)
    @rtype: int
    @return: number of errors found during validation
    """
    objectdb = auditing_objectdb
    reference = model.Event('', '')
    return _validate_model(model.Event.__name__, objectdb, reference)


def _validate_package():
    """
    Validate the Package model
    @rtype: int
    @return: number of errors found during validation
    """
    objectdb = package.PackageApi()._getcollection()
    reference = model.Package('', '', '', '', '', '', '', '')
    return _validate_model(model.Package.__name__, objectdb, reference)


def _validate_package_group():
    """
    Validate the PackageGroup model
    @rtype: int
    @return: number of errors found during validation
    """
    return 0


def _validate_package_group_category():
    """
    Validate the PackageGroupCategory model
    @rtype: int
    @return: number of errors found during validation
    """
    return 0


def _validate_repo():
    """
    Validate the Repo model
    @rtype: int
    @return: number of errors found during validation
    """
    objectdb = repo.RepoApi()._getcollection()
    reference = model.Repo('', '', '')
    return _validate_model(model.Repo.__name__, objectdb, reference)


def _validate_repo_source():
    """
    Validate the RepoSource model
    @rtype: int
    @return: number of errors found during validation
    """
    num_errors = 0
    objectdb = repo.RepoApi()._getcollection()
    reference = model.RepoSource('yum:http://reference.org/reference_repo/')
    for model in objectdb.find():
        source = model['source']
        if source is None:
            continue
        for field, value in reference.items():
            vtype = type(value)
            if field in source and isinstance(source[field], vtype):
                continue
            if field not in source:
                _log.error('model validation failure in RepoSource for Repo %s: field %s is not present' %
                           str(model['_id']), field)
            else:
                _log.error('model validation failure in RepoSource for Repo %s: field %s is not a %s' %
                           str(model['_id']), field, vtype)
    return num_errors


def _validate_user():
    """
    Validate the User model
    @rtype: int
    @return: number of errors found during validation
    """
    objectdb = user.UserApi()._getcollection()
    reference = model.User('', '', '', None)
    return _validate_model(model.User.__name__, objectdb, reference)

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
    num_errors += _validate_errata()
    num_errors += _validate_event()
    num_errors += _validate_package()
    num_errors += _validate_package_group()
    num_errors += _validate_package_group_category()
    num_errors += _validate_repo()
    num_errors += _validate_repo_source()
    num_errors += _validate_user()
    return num_errors
