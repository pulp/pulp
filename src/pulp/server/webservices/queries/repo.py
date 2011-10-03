# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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
Repo module containing repo quries based on HTTP query parameters.
"""

from pulp.server.db.model.resource import Repo
from pulp.server.webservices import http
from pulp.server.webservices.queries.common import OPERATION_FILTERS


def collection():
    """
    Get all of the repos in our Repo db collection, filtered by the query
    parameters.
    @return: list of repo objects
    @rtype: list [SON, ...]
    """
    # XXX implement for v2 of the api, not v1
    valid_filters = []
    valid_filters.extend(OPERATION_FILTERS)
    query_params = http.query_parameters(valid_filters)
    db_collection = Repo.get_collection()
    spec = {}
    fields = []
    db_cursor = db_collection.find(spec, fields=fields or None)


def resource(repo_id):
    """
    Get the repo object specified by the id, with fields filtered by the query
    parameters.
    @param repo_id: unique identifier for the repo
    @type repo_id: str
    @return: repo object if found, otherwise None
    @rtype: SON or None
    """
    valid_filters = ['field']
    query_param = http.query_parameters(valid_filters)
    fields = query_param.get('field', None)
    db_collection = Repo.get_collection()
    repo = db_collection.find_one({'_id': repo_id}, fields=fields)
    return repo


def subcollection_content(repo_id):
    # XXX idea placeholder
    pass
