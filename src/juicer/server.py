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

import gevent.socket
import gevent.ssl
import gevent.wsgi

from juicer.application import wsgi_application


def _create_socket(config):
    address = config.get('server', 'address')
    port = config.getint('server', 'port')
    socket = gevent.socket.tcp_listener((address, port))
    if config.getboolean('server', 'use_ssl'):
        keyfile = config.get('ssl', 'keyfile')
        certfile = config.get('ssl', 'certfile')
        socket = gevent.ssl.SSLSocket(socket, keyfile, certfile)
    return socket


def get_server(config):
    socket = _create_socket(config)
    application = wsgi_application(config)
    server = gevent.wsgi.WSGIServer(socket, application)
    return server