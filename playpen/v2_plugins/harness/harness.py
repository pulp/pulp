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

import base64
import ConfigParser
import httplib
import json
import optparse
import sys
import types

import prompt

# -- constants ----------------------------------------------------------------

REST_COLOR = prompt.COLOR_LIGHT_BLUE
RESPONSE_COLOR = prompt.COLOR_LIGHT_PURPLE

# -- classes ------------------------------------------------------------------

class Harness:

    def __init__(self, connection, script):
        """
        @param connection: must be ready to run (call connect before passing in)
        @type  connection: L{PulpConnection}

        @param script: config file dictating how the harness will run
        @type  script: L{ConfigParser}
        """
        self.connection = connection
        self.script = script

        use_color = self.script.getboolean('output', 'use_color')
        self.prompt = prompt.Prompt(enable_color=use_color)

    # -- script running functionality -----------------------------------------

    def run(self):
        """
        Runs the appropriate commands accroding the script given at instantiation.
        """

        if self.script.getboolean('general', 'run_delete_repo'):
            self.delete_repo()

        if self.script.getboolean('general', 'run_create_repo'):
            self.create_repo()

        if self.script.getboolean('general', 'run_add_importer'):
            self.add_importer()

        if self.script.getboolean('general', 'run_sync_repo'):
            self.sync_repo()

        if self.script.getboolean('general', 'run_list_units'):
            self.list_units()

    def delete_repo(self):
        self._print_divider()

        repo_id = self.script.get('general', 'repo_id')
        url = '/v2/repositories/%s/' % repo_id

        self.prompt.write('Looking up repository [%s] on the server' % repo_id)
        self._print_rest('GET', url, None)
        self._pause()

        status, body = self.connection.GET(url)

        if status == 200:
            self.prompt.write('Repository with ID [%s] already exists and will be deleted' % repo_id)
            self._print_rest('DELETE', url, None)
            self._pause()
            self.connection.DELETE(url)
        elif status == 404:
            self.prompt.write('Repository [%s] did not previously exist on the server' % repo_id)
        else:
            self.prompt.write('Unexpected HTTP status code testing for repository existence [%s]' % status)

    def create_repo(self):
        self._print_divider()

        repo_id = self.script.get('general', 'repo_id')
        url = '/v2/repositories/'
        body = {
            'id'           : repo_id,
            'display_name' : 'Harness Repository: %s' % repo_id
        }

        self.prompt.write('Creating repository with ID [%s]' % repo_id)
        self._print_rest('POST', url, body)
        self._pause()

        status, body = self.connection.POST(url, body)

        self._print_response(status, body)

        if status == 201:
            self.prompt.write('Repository successfully created')
        else:
            self.prompt.write('Creation returned error code [%s]' % status)

    def add_importer(self):
        self._print_divider()

        repo_id = self.script.get('general', 'repo_id')

        importer_config = dict(self.script.items('repository'))

        url = '/v2/repositories/%s/importers/' % repo_id
        body = {
            'importer_type_id' : 'harness_importer',
            'importer_config'  : importer_config,
        }

        self.prompt.write('Adding the harness importer to repository [%s]' % repo_id)
        self.prompt.write('Importer configuration:')
        for k, v in importer_config.items():
            self.prompt.write('    %-15s : %s' % (k, v))

        self._print_rest('POST', url, body)
        self._pause()
        
        status, body = self.connection.POST(url, body)

        self._print_response(status, body)

        if status == 201:
            self.prompt.write('Importer successfully added to repository')
        else:
            self.prompt.write('Addition returned error code [%s]' % status)

    def sync_repo(self):
        self._print_divider()

        repo_id = self.script.get('general', 'repo_id')

        override_config = dict(self.script.items('override'))

        url = '/v2/repositories/%s/actions/sync/' % repo_id
        body = {
            'override_config' : override_config,
        }

        self.prompt.write('Synchronizing repository [%s]' % repo_id)
        self._print_rest('POST', url, body)
        self._pause()

        status, body = self.connection.POST(url, body)

        self._print_response(status, body)

        self.prompt.write('Synchronization complete')

    def list_units(self):
        self._print_divider()

        type_id = 'harness_type_one'
        url = '/v2/content/%s/units/' % type_id

        self.prompt.write('Retrieving list of units of type [%s]' % type_id)
        self._print_rest('GET', url, None)
        self._pause()

        status, body = self.connection.GET(url)

        unit_limit = self.script.getint('output', 'list_units_limit')
        self._print_response(status, body, limit=unit_limit)

        self.prompt.write('Retrieved [%d] units' % len(body))

    # -- utilities ------------------------------------------------------------

    def _pause(self):
        if not self.script.getboolean('general', 'pause'):
            return

        self.prompt.write('')
        result = self.prompt.prompt('Press Enter to continue (ctrl+c to exit)...', allow_empty=True, interruptable=True)

        if result is prompt.ABORT:
            self.prompt.write('Exiting...')
            sys.exit(0)

        self.prompt.write('')
        
    def _print_divider(self):
        self.prompt.write('=' * 60)

    def _print_rest(self, method, url, body):
        if not self.script.getboolean('output', 'print_rest'):
            return

        self.prompt.write('')
        self.prompt.write(self.prompt.color('Method: %s' % method, REST_COLOR))
        self.prompt.write(self.prompt.color('URL:    %s' % url, REST_COLOR))
        if body is not None:
            self.prompt.write(self.prompt.color('Body:   %s' % body, REST_COLOR))
        self.prompt.write('')

    def _print_response(self, status, body, limit=None):
        if not self.script.getboolean('output', 'print_rest'):
            return

        if limit is None or len(body) <= limit:
            indent = self.script.getint('output', 'json_indent')
            formatted_body = json.dumps(body, indent=indent)
        else:
            formatted_body = '<Item Count: %d>' % len(body)

        self.prompt.write('')
        self.prompt.write(self.prompt.color('Response Code: %s' % status, RESPONSE_COLOR))
        self.prompt.write(self.prompt.color('Body:', RESPONSE_COLOR))
        self.prompt.write(self.prompt.color(formatted_body, RESPONSE_COLOR))
        self.prompt.write('')

class PulpConnection:

    def __init__(self, host='localhost', port=443, path_prefix='/pulp/api', user='admin', password='admin'):
        self.host = host
        self.port = port
        self.path_prefix = path_prefix
        self.user = user
        self.password = password

        self.connection = None

    def connect(self):
        self.connection = httplib.HTTPSConnection(self.host, self.port)

    def GET(self, path, **params):
        path = '?'.join((path, self._query_params(params)))
        return self._request('GET', path)

    def OPTIONS(self, path):
        return self._request('OPTIONS', path)

    def PUT(self, path, body):
        return self._request('PUT', path, body)

    def POST(self, path, body=None):
        return self._request('POST', path, body)

    def DELETE(self, path):
        return self._request('DELETE', path)

    def _request(self, method, path, body=None):
        if self.connection is None:
            raise RuntimeError('You must run connect() before making requests')
        if not isinstance(body, types.NoneType):
            body = json.dumps(body)

        raw = ':'.join((self.user, self.password))
        encoded = base64.encodestring(raw)[:-1]
        auth_header = {'Authorization': 'Basic %s' % encoded}

        self.connection.request(method,
                                self.path_prefix + path,
                                body=body,
                                headers=auth_header)
        response = self.connection.getresponse()
        response_body = response.read()
        response_body = json.loads(response_body)

        return response.status, response_body

    def _query_params(self, params):
        for k, v in params.items():
            if isinstance(v, basestring):
                params[k] = [v]
        return '&'.join('%s=%s' % (k, v) for k in params for v in params[k])


if __name__ == '__main__':

    parser = optparse.OptionParser(usage='%s -s SCRIPT_FILE' % __file__)
    parser.add_option('-s', '--script', dest='script', default=None,
                      help='full path to the configuration file dictating how the harness will run')

    options, args = parser.parse_args()
    if options.script is None:
        parser.print_help()
        sys.exit(1)

    script = ConfigParser.SafeConfigParser()
    script.read(options.script)

    connection = PulpConnection()
    connection.connect()

    harness = Harness(connection, script)
    harness.run()
