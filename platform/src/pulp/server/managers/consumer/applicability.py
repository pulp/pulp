# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Contains content applicability management classes
"""

from gettext import gettext as _
from logging import getLogger

from pulp.server.db.model.consumer import RepoProfileApplicability


_LOG = getLogger(__name__)


class DoesNotExist(Exception):
    """
    An Exception to be raised when a get() is called on a manager with query parameters that do not
    match an object in the database.
    """
    pass


class MultipleObjectsReturned(Exception):
    """
    An Exception to be raised when a get() is called on a manager that results in more than one
    object being returned.
    """
    pass


class RepoProfileApplicabilityManager(object):
    """
    This class is useful for querying for RepoProfileApplicability objects in the database.
    """
    def create(self, profile_hash, repo_id, profile, applicability):
        """
        Create and return a RepoProfileApplicability object.

        :param profile_hash:  The hash of the profile that this object contains applicability data
                              for
        :type  profile_hash:  basestring
        :param repo_id:       The repo ID that this applicability data is for
        :type  repo_id:       basestring
        :param profile:       The entire profile that resulted in the profile_hash
        :type  profile:       object
        :param applicability: A dictionary structure mapping unit type IDs to lists of applicable
                              Unit IDs.
        :type  applicability: dict
        :return:              A new RepoProfileApplicability object
        :rtype:               pulp.server.db.model.consumer.RepoProfileApplicability
        """
        applicability = RepoProfileApplicability(
            profile_hash=profile_hash, repo_id=repo_id, profile=profile,
            applicability=applicability)
        applicability.save()
        return applicability

    def filter(self, query_params):
        """
        Get a list of RepoProfileApplicability objects with the given MongoDB query dict.

        :param query_params: A MongoDB query dictionary that selects RepoProfileApplicability
                             documents
        :type  query_params: dict
        :return:             A list of RepoProfileApplicability objects that match the given query
        :rtype:              list
        """
        collection = RepoProfileApplicability.get_collection()
        mongo_applicabilities = collection.find(query_params)
        applicabilities = [RepoProfileApplicability(**dict(applicability)) \
                           for applicability in mongo_applicabilities]
        return applicabilities

    def get(self, query_params):
        """
        Get a single RepoProfileApplicability object with the given MongoDB query dict. This
        will raise a DoesNotExist if no such object exists. It will also raise
        MultipleObjectsReturned if the query_dict was not specific enough to match just one
        RepoProfileApplicability object.

        :param query_params: A MongoDB query dictionary that selects a single
                             RepoProfileApplicability document
        :type  query_params: dict
        :return:             A RepoProfileApplicability object that matches the given query
        :rtype:              pulp.server.db.model.consumer.RepoProfileApplicability
        """
        applicability = self.filter(query_params)
        if not applicability:
            raise DoesNotExist(_('The RepoProfileApplicability object does not exist.'))
        if len(applicability) > 1:
            error_message = _('The given query matched %(num)s documents.')
            error_message = error_message % {'num': len(applicability)}
            raise MultipleObjectsReturned(error_message)
        return applicability[0]
# Instantiate one of the managers on the object it manages for convenience
RepoProfileApplicability.objects = RepoProfileApplicabilityManager()