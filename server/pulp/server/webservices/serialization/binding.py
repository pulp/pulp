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

import link

from pulp.server.managers import factory as manager_factory
from pulp.server.exceptions import MissingResource


def serialize(bind, include_details=True):
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

    repo_id = bind['repo_id']
    distributor_id = bind['distributor_id']

    # href
    #
    # 1019155 - There are three URLs that currently support bindings:
    # 1. /consumers/<consumer_id>/bindings/
    # 2. /consumers/<consumer_id>/bindings/<repo_id>/
    # 3. /consumers/<consumer_id>/bindings/<repo_id>/<distributor_id>/
    #
    # Make sure we return the third URL for an individual binding.

    href = link.current_link_obj()

    href_url = href['_href']

    if href_url.count(repo_id) == 0:
        href = link.child_link_obj(repo_id, distributor_id)

    elif href_url.count(distributor_id) == 0:
        href = link.child_link_obj(distributor_id)

    serialized.update(href)

    repo_distributor_manager = manager_factory.repo_distributor_manager()

    # type_id
    try:
        distributor = repo_distributor_manager.get_distributor(repo_id, distributor_id)

    except MissingResource:
        if include_details:
            raise

    else:
        serialized['type_id'] = distributor['distributor_type_id']

    # details
    if include_details:
        details = repo_distributor_manager.create_bind_payload(repo_id, distributor_id,
                                                               bind['binding_config'])
        serialized['details'] = details

    return serialized
