# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

"""
HTTP test server for writing tests against an "external" server.
"""

import threading
from BaseHTTPServer import HTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler


class HTTPStaticTestServer(object):
    """
    Static test server that server files from the local directory and
    sub-directories. Highly recommended that each test suite puts the files it
    wants served into a custom sub-directory under 'data/'. Then tests can
    reach the files by using the url:
    http://localhost:8088/data/<custom-sub-directory>/<file>

    This server is run in a thread over the local loopback and should be
    started and stopped on each test or test suite run.

    It's recommended that start be put in setUpClass and stop be put in
    tearDownClass to avoid the overhead of starting and stopping on each test
    run.
    """

    def __init__(self, port=8088):
        self.server = HTTPServer(('', port), SimpleHTTPRequestHandler)
        self.server.timeout = 0.1 # timeout after a tenth of a second
        self._is_running = False
        self._server_thread = None

    # server loop --------------------------------------------------------------

    def _serve(self):
        while self._is_running:
            self.server.handle_request()

    def start(self):
        self._is_running = True
        self._server_thread = threading.Thread(target=self._serve)
        self._server_thread.setDaemon(True)
        self._server_thread.start()

    def stop(self):
        self._is_running = False
        self._server_thread.join()
        self._server_thread = None
