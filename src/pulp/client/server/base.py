# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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


class ServerRequestError(Exception):
    """
    Exception to indicate a less than favorable response from the server.
    The arguments are [0] the response status as an integer and
    [1] the response message as a dict, if we managed to decode from json,
    or a str if we didn't
    """
    pass


class Server(object):
    """
    Base server class.
    @ivar host: host name of the pulp server
    @ivar port: port the pulp server is listening on (443)
    @ivar protocol: protocol the pulp server is using (http, https)
    @ivar path_prefix: mount point of the pulp api (/pulp/api)
    @ivar headers: dictionary of http headers to send in requests
    """

    def __init__(self, host, port=80, protocol='http', path_prefix=''):
        assert protocol in ('http', 'https')

        self.host = host
        self.port = port
        self.protocol = protocol
        self.path_prefix = path_prefix
        self.headers = {}

    # credentials setters -----------------------------------------------------

    def set_basic_auth_credentials(self, username, password):
        """
        Set username and password credentials for http basic auth
        @type username: str
        @param username: username
        @type password: str
        @param password: password
        """
        raise NotImplementedError('base server class method called')

    def set_ssl_credentials(self, certfile, keyfile):
        """
        Set ssl certificate and public key credentials
        @type certfile: str
        @param certfile: absolute path to the certificate file
        @type keyfile: str
        @param keyfile: absolute path to the public key file
        @raise RuntimeError: if either of the files cannot be found or read
        """
        raise NotImplementedError('base server class method called')

    # request methods ---------------------------------------------------------

    def DELETE(self, path):
        """
        Send a DELETE request to the pulp server.
        @type path: str
        @param path: path of the resource to delete
        @rtype: (int, dict or None or str)
        @return: tuple of the http response status and the response body
        @raise ServerRequestError: if the request fails
        """
        raise NotImplementedError('base server class method called')

    def GET(self, path, queries=()):
        """
        Send a GET request to the pulp server.
        @type path: str
        @param path: path of the resource to get
        @type queries: dict or iterable of tuple pairs
        @param queries: dictionary of iterable of key, value pairs to send as
                        query parameters in the request
        @rtype: (int, dict or None or str)
        @return: tuple of the http response status and the response body
        @raise ServerRequestError: if the request fails
        """
        raise NotImplementedError('base server class method called')

    def HEAD(self, path):
        """
        Send a HEAD request to the pulp server.
        @type path: str
        @param path: path of the resource to check
        @rtype: (int, dict or None or str)
        @return: tuple of the http response status and the response body
        @raise ServerRequestError: if the request fails
        """
        raise NotImplementedError('base server class method called')

    def POST(self, path, body=None):
        """
        Send a POST request to the pulp server.
        @type path: str
        @param path: path of the resource to post to
        @type body: dict or None
        @param body: (optional) dictionary for json encoding of post parameters
        @rtype: (int, dict or None or str)
        @return: tuple of the http response status and the response body
        @raise ServerRequestError: if the request fails
        """
        raise NotImplementedError('base server class method called')

    def PUT(self, path, body):
        """
        Send a PUT request to the pulp server.
        @type path: str
        @param path: path of the resource to put
        @type body: dict
        @param body: dictionary for json encoding of resource
        @rtype: (int, dict or None or str)
        @return: tuple of the http response status and the response body
        @raise ServerRequestError: if the request fails
        """
        raise NotImplementedError('base server class method called')
