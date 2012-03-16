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
import datetime
import httplib
import json
import sys
import types

import prompt

# -- constants ----------------------------------------------------------------

REST_COLOR = prompt.COLOR_LIGHT_BLUE
RESPONSE_COLOR = prompt.COLOR_LIGHT_PURPLE
TIME_COLOR = prompt.COLOR_LIGHT_CYAN
PLUGIN_LOG_COLOR = prompt.COLOR_YELLOW
ERROR_COLOR = prompt.COLOR_LIGHT_RED

# -- classes ------------------------------------------------------------------

class SilentPrompt(prompt.Prompt):
    def write(self, content, new_line=True):
        pass

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

        if self.script.getboolean('output', 'silent'):
            self.prompt = SilentPrompt()
        else:
            self.prompt = prompt.Prompt(enable_color=use_color)

    # -- script running functionality -----------------------------------------

    def run(self):
        """
        Runs the appropriate commands according to the script given at instantiation.
        """

        if self.script.getboolean('general', 'run_delete_repo'):
            self._assert_status(self.delete_repo(), no_fail=True)

        if self.script.getboolean('general', 'run_create_repo'):
            self._assert_status(self.create_repo())

        if self.script.getboolean('general', 'run_add_importer'):
            self._assert_status(self.add_importer())

        if self.script.getboolean('general', 'run_add_distributor'):
            self._assert_status(self.add_distributor())

        if self.script.getboolean('general', 'run_sync_repo'):
            self._assert_status(self.sync_repo())

        if self.script.getboolean('general', 'run_sync_history'):
            self._assert_status(self.load_sync_history())

        if self.script.getboolean('general', 'run_publish_repo'):
            self._assert_status(self.publish_repo())

        if self.script.getboolean('general', 'run_publish_history'):
            self._assert_status(self.load_publish_history())

        if self.script.getboolean('general', 'run_associate_units'):
            self._assert_status(self.associate_units())

        if self.script.getboolean('general', 'run_list_units'):
            self._assert_status(self.list_units())

        if self.script.getboolean('general', 'run_list_associations'):
            self._assert_status(self.list_associated_units())

    def delete_repo(self):
        self._print_divider()

        repo_id = self.script.get('general', 'repo_id')
        url = '/v2/repositories/%s/' % repo_id

        self.prompt.write('Looking up repository [%s] on the server' % repo_id)
        self._pause()
        status, body = self._call('GET', url, None)

        if status == 200:
            self.prompt.write('Repository with ID [%s] already exists and will be deleted' % repo_id)
            self._call('DELETE', url, None)
            self._pause()
            self.connection.DELETE(url)
        elif status == 404:
            self.prompt.write('Repository [%s] did not previously exist on the server' % repo_id)
        else:
            self.prompt.write('Unexpected HTTP status code testing for repository existence [%s]' % status)

        return status

    def create_repo(self):
        self._print_divider()

        repo_id = self.script.get('general', 'repo_id')
        url = '/v2/repositories/'
        body = {
            'id'           : repo_id,
            'display_name' : 'Harness Repository: %s' % repo_id
        }

        self.prompt.write('Creating repository with ID [%s]' % repo_id)
        self._pause()
        status, body = self._call('POST', url, body)

        self._print_response(status, body)

        if status == 201:
            self.prompt.write('Repository successfully created')
        else:
            self.prompt.write('Creation returned error code [%s]' % status)

        return status

    def add_importer(self):
        self._print_divider()

        repo_id = self.script.get('general', 'repo_id')

        importer_config_type = self.script.get('general', 'importer_config_type')
        importer_config = dict(self.script.items(importer_config_type))
        importer_type_id = self.script.get('general', 'importer_type_id')

        url = '/v2/repositories/%s/importers/' % repo_id
        body = {
            'importer_type_id' : importer_type_id,
            'importer_config'  : importer_config,
        }

        self.prompt.write('Adding the harness importer to repository [%s]' % repo_id)
        self.prompt.write('Importer configuration:')
        for k, v in importer_config.items():
            self.prompt.write('    %-15s : %s' % (k, v))

        self._pause()
        status, body = self._call('POST', url, body)

        self._print_response(status, body)

        if status == 201:
            self.prompt.write('Importer successfully added to the repository')
        else:
            self.prompt.write('Addition returned error code [%s]' % status)

        return status

    def add_distributor(self):
        self._print_divider()

        repo_id = self.script.get('general', 'repo_id')

        distributor_config_type = self.script.get('general', 'distributor_config_type')
        distributor_config = dict(self.script.items(distributor_config_type))
        distributor_type_id = self.script.get('general', 'distributor_type_id')

        url = '/v2/repositories/%s/distributors/' % repo_id
        body = {
            'distributor_type_id' : distributor_type_id,
            'distributor_config'  : distributor_config,
            'auto_publish'        : False,
            'distributor_id'      : 'dist_1',
        }

        self.prompt.write('Adding the %s distributor to repository [%s]' % (distributor_type_id, repo_id))
        self.prompt.write('Distributor configuration:')
        for k, v in distributor_config.items():
            self.prompt.write('    %-15s : %s' % (k, v))

        self._pause()
        status, body = self._call('POST', url, body)

        self._print_response(status, body)

        if status == 201:
            self.prompt.write('Distributor successfully added to the repository')
        else:
            self.prompt.write('Addition returned error code [%s]' % status)

        return status

    def sync_repo(self):
        self._print_divider()

        repo_id = self.script.get('general', 'repo_id')
        override_config = dict(self.script.items('sync-override'))

        url = '/v2/repositories/%s/actions/sync/' % repo_id
        body = {
            'override_config' : override_config,
        }

        self.prompt.write('Synchronizing repository [%s]' % repo_id)
        self._pause()
        status, body = self._call('POST', url, body)

        self._print_response(status, body)

        self.prompt.write('Synchronization complete')

        return status

    def publish_repo(self):
        self._print_divider()

        repo_id = self.script.get('general', 'repo_id')
        distributor_id = 'dist_1'
        override_config = dict(self.script.items('publish-override'))

        url = '/v2/repositories/%s/actions/publish/' % repo_id
        body = {
            'id'              : distributor_id,
            'override_config' : override_config,
        }

        self.prompt.write('Publishing repository [%s]' % repo_id)
        self._pause()
        status, body = self._call('POST', url, body)

        self._print_response(status, body)

        self.prompt.write('Publish complete')

        return status

    def load_sync_history(self):
        self._print_divider()

        repo_id = self.script.get('general', 'repo_id')

        url = '/v2/repositories/%s/sync_history/?limit=1' % repo_id

        self.prompt.write('Retrieving the results of the last sync')
        self._pause()
        status, body = self._call('GET', url, None)

        self._print_response(status, body)

        item = body[0]
        self.prompt.write('Results of the last sync')
        self.prompt.write('  Result:             %s' % item['result'])
        self.prompt.write('  Importer ID:        %s' % item['importer_id'])
        self.prompt.write('  Started:            %s' % item['started'])
        self.prompt.write('  Completed:          %s' % item['completed'])
        self.prompt.write('  Added Unit Count:   %s' % item['added_count'])
        self.prompt.write('  Updated Unit Count: %s' % item['updated_count'])
        self.prompt.write('  Removed Unit Count: %s' % item['removed_count'])
        self.prompt.write('  Report Summary:     %s' % item['summary'])
        self.prompt.write('  Report Details:')
        self.prompt.write('---')
        self.prompt.write(self.prompt.color(item['details'], PLUGIN_LOG_COLOR))
        self.prompt.write('---')
    
        return status

    def load_publish_history(self):
        self._print_divider()

        repo_id = self.script.get('general', 'repo_id')
        distributor_id = 'dist_1'

        url = '/v2/repositories/%s/publish_history/%s/?limit=1' % (repo_id, distributor_id)
        self._pause()
        status, body = self._call('GET', url, None)

        self._print_response(status, body)

        item = body[0]
        self.prompt.write('Results of the last publish')
        self.prompt.write('  Result:             %s' % item['result'])
        self.prompt.write('  Distributor ID:     %s' % item['distributor_id'])
        self.prompt.write('  Started:            %s' % item['started'])
        self.prompt.write('  Completed:          %s' % item['completed'])
        self.prompt.write('  Report Summary:     %s' % item['summary'])
        self.prompt.write('  Report Details:')
        self.prompt.write('---')
        self.prompt.write(self.prompt.color(item['details'], PLUGIN_LOG_COLOR))
        self.prompt.write('---')

        return status

    def associate_units(self):
        self._print_divider()

        source_repo_id = self.script.get('associate', 'source_repo_id')
        dest_repo_id = self.script.get('associate', 'dest_repo_id')
        type_id = 'harness_type_one'

        url = '/v2/repositories/%s/actions/associate/' % dest_repo_id

        # Build up criteria
        criteria = {'type_ids' : [type_id]}

        self._unit_filter('associate', 'search_1', criteria)
        self._unit_filter('associate', 'search_2', criteria)
        self._unit_filter('associate', 'random_1', criteria)

        # Assemble the parameters
        body = {'source_repo_id' : source_repo_id,
                'criteria' : criteria}

        self.prompt.write('Associating units from [%s] to [%s]' % (source_repo_id, dest_repo_id))
        self.prompt.write('')
        self.prompt.write('Association Criteria:')
        indent = self.script.getint('output', 'json_indent')
        formatted_body = json.dumps(criteria, indent=indent)
        self.prompt.write(formatted_body)

        self._pause()
        status, body = self._call('POST', url, body)

        self._print_response(status, body)

        self.prompt.write('Association complete')

    def list_units(self):
        self._print_divider()

        type_id = self.script.get('general', 'list_content_id')
        url = '/v2/content/%s/units/' % type_id

        self.prompt.write('Retrieving list of units of type [%s]' % type_id)
        self._pause()
        status, body = self._call('GET', url, None)

        unit_limit = self.script.getint('output', 'list_units_limit')
        self._print_response(status, body, limit=unit_limit)

        self.prompt.write('Retrieved [%d] units' % len(body))

        return status

    def list_associated_units(self):
        self._print_divider()

        repo_id = self.script.get('general', 'repo_id')
        type_id = 'harness_type_one'
        url = '/v2/repositories/%s/search/units/' % repo_id

        # -- Build up criteria ------------------------------------------------

        query = {'type_ids' : [type_id]}

        # Unit Filters

        self._unit_filter('query', 'search_1', query)
        self._unit_filter('query', 'search_2', query)
        self._unit_filter('query', 'random_1', query)

        # Sort

        def sort(name, query):

            if self.script.has_option('query', name + '_sort'):
                sort = query.setdefault('sort', {})

                direction = 'ascending'
                if self.script.has_option('query', 'sort_direction'):
                    direction = self.script.get('query', 'sort_direction')

                sort_list = sort.setdefault(name, [])
                for f in self.script.get('query', name + '_sort').split():
                    sort_list.append([f, direction])

        sort('association', query)
        sort('unit', query)

        # Limit & Skip

        if self.script.has_option('query', 'limit'):
            query['limit'] = self.script.getint('query', 'limit')

        if self.script.has_option('query', 'skip'):
            query['skip'] = self.script.getint('query', 'skip')

        # Fields

        if self.script.has_option('query', 'unit_fields'):
            fields = query.setdefault('fields', {})
            fields['unit'] = self.script.get('query', 'unit_fields').split()

        # -- Run the query ----------------------------------------------------
        self.prompt.write('Retrieving associated units of type [%s]' % type_id)
        self.prompt.write('')
        self.prompt.write('Query Criteria:')
        indent = self.script.getint('output', 'json_indent')
        formatted_body = json.dumps(query, indent=indent)
        self.prompt.write(formatted_body)

        self._pause()
        status, body = self._call('POST', url, {'query' : query})
        self._print_response(status, body)
        self.prompt.write('')

        #  -- Report ----------------------------------------------------------
        self.prompt.write('Number of matching units: %s' % len(body))
        self.prompt.write('')

        headers = ('Unit ID', 'Type ID', 'Name', 'Search 1', 'Search 2', 'Random 1')
        report_template = '%-10s  %-10s  %-15s  %-10s  %-10s  %-10s'
        header_line = report_template % headers
        divider = '-' * len(header_line)

        self.prompt.write(self.prompt.color(header_line, prompt.COLOR_BG_BLUE))
        # self.prompt.write(header_line)
        self.prompt.write(divider)

        flipper = 0
        highlights = (prompt.COLOR_WHITE, prompt.COLOR_LIGHT_PURPLE)
        for unit in body:
            unit_id = unit['unit_id'][:10]
            type_id = unit['unit_type_id'][len(unit['unit_type_id']) - 10:]
            created = unit['created']
            updated = unit['updated']

            missing = self.prompt.color('<missing>', prompt.COLOR_LIGHT_GRAY)

            name = unit['metadata'].get('name', missing)
            search_1 = unit['metadata'].get('search_1', missing)
            search_2 = unit['metadata'].get('search_2', missing)
            random_1 = unit['metadata'].get('random_1', missing)

            r = report_template % (unit_id, type_id, name, search_1, search_2, random_1)
            self.prompt.write(self.prompt.color(r, highlights[flipper % len(highlights)]))

            flipper += 1
            flipper = 0 # comment to enable per row highlighting

        self.prompt.write('')

    # -- utilities ------------------------------------------------------------

    def _unit_filter(self, script_section, filter_name, query):

        if self.script.has_option(script_section, filter_name):
            filters = query.setdefault('filters', {})
            unit_filters = filters.setdefault('unit', {})

            # Minor hack to support regex
            filter_value = self.script.get(script_section, filter_name)
            if '*' in filter_value:
                filter_value = {'$regex' : filter_value}

            unit_filters[filter_name] = filter_value

    def _assert_status(self, status, no_fail=False):
        """
        Determines if the script should abort based on the given HTTP status.
        """

        if no_fail:
            return
        
        if status > 299:
            self.prompt.write('')
            self.prompt.write(self.prompt.color('Error HTTP status code from last command [%d]' % status, ERROR_COLOR))
            self.prompt.write('')
            sys.exit(1)

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
        self.prompt.write('')
        self.prompt.write('=' * 60)

    def _call(self, method, url, body):
        print_rest = self.script.getboolean('output', 'print_rest')
        print_call_time = self.script.getboolean('output', 'print_call_time')

        start = datetime.datetime.now()
        func = getattr(self.connection, method)
        if body is None:
            r_status, r_body = func(url)
        else:
            r_status, r_body = func(url, body)
        end = datetime.datetime.now()

        if print_rest:
            self.prompt.write('')
            self.prompt.write(self.prompt.color('Method: %s' % method, REST_COLOR))
            self.prompt.write(self.prompt.color('URL:    %s' % url, REST_COLOR))
            if body is not None:
                self.prompt.write(self.prompt.color('Body:' % body, REST_COLOR))
                indent = self.script.getint('output', 'json_indent')
                formatted_body = json.dumps(body, indent=indent)
                self.prompt.write(self.prompt.color(formatted_body, REST_COLOR))

        if print_call_time:
            ellapsed = end - start
            self.prompt.write(self.prompt.color('Call Time: %d seconds' % ellapsed.seconds, TIME_COLOR))

        return r_status, r_body

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
        try:
            response_body = json.loads(response_body)
        except:
            pass

        return response.status, response_body

    def _query_params(self, params):
        for k, v in params.items():
            if isinstance(v, basestring):
                params[k] = [v]
        return '&'.join('%s=%s' % (k, v) for k in params for v in params[k])


if __name__ == '__main__':

    if len(sys.argv) == 1:
        print('Usage: harness.py SCENARIO_FILE')
        sys.exit(1)

    script = ConfigParser.SafeConfigParser()
    script.read('scenarios/_default.ini')
    script.read(sys.argv[1])

    if len(sys.argv) > 2:
        for o in sys.argv[2:]:
            key, value = o.split('=')
            section, option = key.split('.')
            
            script.set(section, option, value)
            
    connection = PulpConnection()
    connection.connect()

    harness = Harness(connection, script)
    harness.run()
