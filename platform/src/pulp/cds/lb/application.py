# -*- coding: utf-8 -*-
#
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

import itertools
import socket
import storage


APPLICATION_PREFIX = '/pulp/mirror'

CODE_OK = '200 OK'
CODE_NOT_IN_GROUP = '404 Not Found'

def process_request(environ, start_response):
    """
    WSGI entry point for the CDS load balancer application.
    """

    # If the members list is requested, don't rotate the permutations and just
    # return the list of members. If not, assume a load balancing call and take
    # steps to increment the balancer and generate full URLs.
    if 'members' in environ['QUERY_STRING']:
        status, output = _do_members()
    else:
        status, output = _do_balancing(environ['REQUEST_URI'])

    # Prepare to return to the caller
    response_headers = [('Content-type', 'text/plain'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]

def _do_balancing(request_uri):
    """
    Performs the load balancing, using the given request URI as the
    destination URL for each server.

    @return: tuple of HTTP status code reflecting what was found and list
             of full URLs to access the given URI, one per line
    @rtype:  (str, str)
    """

    # Determine the balancing order
    cds_hostnames = _next_permutation()

    # Determine the repo URLs by merging in the requested repo with the
    # new CDS permutation
    requested_repo = _requested_dir(request_uri)

    repo_urls = []

    # If the CDS is not in a group, just return a reference to the CDS itself
    if len(cds_hostnames) == 0:
        cds_hostnames.append(socket.gethostname())

    # Assemble the repo URLs
    for cds in cds_hostnames:
        url = 'https://%s/pulp/repos/%s' % (cds, requested_repo)
        repo_urls.append(url)

    # Package for returning to the caller
    output = '\n'.join(repo_urls)

    return CODE_OK, output

def _do_members():
    """
    If a members check was called, simply read in the list of servers and
    return that.

    @return: tuple of HTTP status code reflecting what was found and list of
             members in the load balancer, one per line
    @rtype:  (str, str)
    """
    file_storage = storage.FilePermutationStore()
    file_storage.open()

    members = file_storage.permutation

    file_storage.close()

    if len(members) == 0:
        status = CODE_NOT_IN_GROUP
        output = ''
    else:
        status = CODE_OK
        output = '\n'.join(members)

    return status, output

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
    file_storage.save()
    file_storage.close()

    return next