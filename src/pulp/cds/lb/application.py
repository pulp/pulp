# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 Red Hat, Inc.
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

import itertools
import storage


APPLICATION_PREFIX = '/pulp/mirror'


def process_request(environ, start_response):
    """
    WSGI entry point for the CDS load balancer application.
    """
    status = '200 OK'

    # Determine the balancing order
    next = _next_permutation()

    # Determine the repo URLs by merging in the requested repo with the
    # new CDS permutation
    requested_repo = _requested_dir(environ['REQUEST_URI'])

    repo_urls = []
    for cds in next:
        url = 'https://%s%s' % (cds, requested_repo)
        repo_urls.append(url)

    # Package for returning to the caller
    output = '\n'.join(repo_urls)

    response_headers = [('Content-type', 'text/plain'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]

def _requested_dir(request_uri):
    """
    Strips off the relative URL for the CDS load balancer web application
    and returns the portion of the request that represents what was
    requested.

    @param request_uri: full request URI, including the relative path
                        (ex: /pulp/mirror/repo/fedora-14/x86_64)
    @type  request_uri: str
    """
    return request_uri[len(APPLICATION_PREFIX):]

def _next_permutation():
    """
    Takes the given list of values and rotates them, returning a new
    list with the same items in a new order.

    @return: list of CDS hostnames to be used in load balancing consideration;
             may be empty
    @rtype:  list of str
    """

    file_storage = storage.FilePermutationStore()
    file_storage.open()

    base = file_storage.permutation
    next = list(itertools.chain(base[1:], base[:1]))

    file_storage.permutation = next
    file_storage.close()

    return next