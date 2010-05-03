#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright © 2010 Red Hat, Inc.
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

__author__ = 'Jason L Connor <jconnor@redhat.com>'
__version__ = '0.0.0'

import gevent.socket
import gevent.ssl
import gevent.wsgi


def hello_application(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return ['Hello World!']


def _create_socket(config):
    #address = config.get('server', 'address')
    #port = config.getint('server', 'port')
    address = '127.0.0.1'
    port = 8311
    socket = gevent.socket.tcp_listener((address, port))
    #if config.getbool('server', 'use_ssl'):
    if False:
        keyfile = config.get('ssl', 'keyfile')
        certfile = config.get('ssl', 'certfile')
        socket = gevent.ssl.SSLSocket(socket, keyfile, certfile)
    return socket


def get_server(config):
    server = gevent.wsgi.WSGIServer(_create_socket(config),
                                    hello_application)
    return server

# testing ---------------------------------------------------------------------

if __name__ == '__main__':
    pass