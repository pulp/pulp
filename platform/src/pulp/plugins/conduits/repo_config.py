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
Repo Config Conduit

This conduit provides the utility methods needed by the distributors API for configuration validation.
"""

import logging

from pulp.server.db.model.repository import RepoDistributor

_LOG = logging.getLogger(__name__)


class RepoConfigConduit(object):

    def __init__(self, distributor_type):
        self.distributor_type = distributor_type

    def get_repo_distributors_by_relative_url(self, rel_url):
        """
        Get the config repo_id and config objects matching a given relative URL

        :param rel_url: a relative URL for a distributor config
        :type  rel_url: str

        :return: a list of repository configurations whose configuration conflicts with rel_url
        :rtype:  list
        """
        # build a list of all the sub urls that could conflict with the provided URL
        current_url_pieces = [x for x in rel_url.split("/") if x]
        matching_url_list = []
        workingUrl = "/"
        for piece in current_url_pieces:
            workingUrl += piece
            matching_url_list.append(workingUrl)
            workingUrl += "/"

        #search for all the sub url as well as any url that would fall within the specified url
        spec = {'$or': [{'config.relative_url': {'$regex': '^' + workingUrl + '.*'}},
                        {'config.relative_url': {'$in': matching_url_list}}]}
        projection = {'repo_id': 1, 'config': 1}
        items = list(RepoDistributor.get_collection().find(spec, projection))
        return items
