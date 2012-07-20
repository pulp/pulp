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
Module for binding serialization.
"""

from pulp.server.managers import factory as manager_factory
import link

def serialize(bind):
    """
    Construct a REST object to be returned.
    Add _href and augments information used by the caller
    to consume published content.
    @param bind: A bind model/SON object.
    @type bind: dict/SON
    @return: A bind REST object.
        {consumer_id:<str>,
         repo_id:<str>,
         distributor_id:<str>,
         href:<str>,
         type_id:<str>,
         details:<dict>}
    @rtype: dict
    """
    # bind
    serialized = dict(bind)

    # href
    href = link.child_link_obj(
        bind['consumer_id'],
        bind['repo_id'],
        bind['distributor_id'])
    serialized.update(href)

    # repository
    repo_query_manager = manager_factory.repo_query_manager()
    repo = repo_query_manager.get_repository(bind['repo_id'])
    serialized['repository'] = dict(repo)

    # type_id
    repo_distributor_manager = manager_factory.repo_distributor_manager()
    distributor = repo_distributor_manager.get_distributor(
        bind['repo_id'],
        bind['distributor_id'])
    serialized['type_id'] = distributor['distributor_type_id']

    # details
    details = repo_distributor_manager.create_bind_payload(
        bind['repo_id'],
        bind['distributor_id'])
    serialized['details'] = details

    return serialized
