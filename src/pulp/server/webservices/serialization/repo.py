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
Module for repo serialization.
"""

from pulp.server.cds import round_robin
from pulp.server.webservices import http

# contstants -------------------------------------------------------------------

REPO_URI_PATH = 'pulp/repos'

COLLECTION_HREF = http.API_HREF + '/repositories'
RESOURCE_HREF = COLLECTION_HREF + '/%s'

# repo serialization api -------------------------------------------------------

# XXX this is all v1 api, not v2

def href(repo):
    """
    Generate the href for the repo.
    NOTE this is the location of the repo resource in the REST api.
    @param repo: repo to generate href for
    @type repo: SON or dict
    @return: repo's href
    @rtype: str
    """
    href_ = RESOURCE_HREF % repo['id']
    return http.ensure_ending_slash(href_)


def uri(repo):
    """
    Generate the uri for the repo.
    NOTE this is not the location of the repo resource, it is the published uri.
    @param repo: repo to generate uri for
    @type repo: SON or dict
    @return: repo's uri
    @rtype: str
    """
    # not published: no repo uri
    if not repo['publish']:
        return None
    # use cds uri first
    cds = round_robin._find_association(repo['id'])
    if cds is not None:
        return cds['next_permutation'][0]
    # no cds association: build local uri
    request_uri = http.request_url()
    uri_prefix = request_uri.split(http.API_HREF)[0]
    uri_suffix = repo.get('relative_path', None)
    if uri_suffix is None:
        uri_suffix = repo['id']
    uri_ = '/'.join((uri_prefix, REPO_URI_PATH, uri_suffix))
    return http.ensure_ending_slash(uri_)
