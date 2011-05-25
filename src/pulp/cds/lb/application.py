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


APPLICATION_PREFIX = '/pulp/mirror'


def process_request(environ, start_response):
    """
    WSGI entry point for the CDS load balancer application.
    """
    status = '200 OK'

    requested_repo = _requested_dir(environ['REQUEST_URI'])

    output = 'https://SOMETHING-HERE%s' % requested_repo

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