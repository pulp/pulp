# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os

from pulp.client.commands import options
from pulp.client.commands.repo import cudl
from pulp.client.extensions.core import TAG_SUCCESS
from pulp.common.json_compat import json

from pulp_rpm.common import ids
from pulp_rpm.extension.admin import repo, repo_options
import rpm_support_base


DATA_DIR = os.path.abspath(os.path.dirname(__file__)) + '/data/'


class RpmRepoCreateCommandTests(rpm_support_base.PulpClientTests):

    def test_create_structure(self):
        command = repo.RpmRepoCreateCommand(self.context)

        # Ensure the required option groups
        found_group_names = set([o.name for o in command.option_groups])
        expected_group_names = set(repo_options.ALL_GROUP_NAMES)
        self.assertEqual(found_group_names, expected_group_names)

        # Ensure the correct method is wired up
        self.assertEqual(command.method, command.run)

        # Ensure the correct metadata
        self.assertEqual(command.name, 'create')
        self.assertEqual(command.description, cudl.DESC_CREATE)

    def test_run(self):
        # Setup
        cert_file = os.path.join(DATA_DIR, 'cert.crt')
        cert_key = os.path.join(DATA_DIR, 'cert.key')
        ca_cert = os.path.join(DATA_DIR, 'valid_ca.crt')
        gpg_key = os.path.join(DATA_DIR, 'cert.key') # contents shouldn't matter

        data = {
            options.OPTION_REPO_ID.keyword : 'test-repo',
            options.OPTION_NAME.keyword : 'Test Name',
            options.OPTION_DESCRIPTION.keyword : 'Test Description',
            options.OPTION_NOTES.keyword : {'a' : 'a'},
            repo_options.OPT_FEED.keyword : 'http://localhost',
            repo_options.OPT_NEWEST.keyword : True,
            repo_options.OPT_SKIP.keyword : [ids.TYPE_ID_RPM],
            repo_options.OPT_VERIFY_SIZE.keyword : True,
            repo_options.OPT_VERIFY_CHECKSUM.keyword : True,
            repo_options.OPT_REMOVE_OLD.keyword : True,
            repo_options.OPT_RETAIN_OLD_COUNT.keyword : 2,
            repo_options.OPT_PROXY_URL.keyword : 'http://localhost',
            repo_options.OPT_PROXY_PORT.keyword : 80,
            repo_options.OPT_PROXY_USER.keyword : 'user',
            repo_options.OPT_PROXY_PASS.keyword : 'pass',
            repo_options.OPT_MAX_SPEED.keyword : 1024,
            repo_options.OPT_NUM_THREADS.keyword : 8,
            repo_options.OPT_FEED_CA_CERT.keyword : ca_cert,
            repo_options.OPT_VERIFY_FEED_SSL.keyword : True,
            repo_options.OPT_FEED_CERT.keyword : cert_file,
            repo_options.OPT_FEED_KEY.keyword : cert_key,
            repo_options.OPT_RELATIVE_URL.keyword : '/repo',
            repo_options.OPT_SERVE_HTTP.keyword : True,
            repo_options.OPT_SERVE_HTTPS.keyword : True,
            repo_options.OPT_CHECKSUM_TYPE.keyword : 'sha256',
            repo_options.OPT_GPG_KEY.keyword : gpg_key,
            repo_options.OPT_HOST_CA.keyword : ca_cert,
            repo_options.OPT_AUTH_CA.keyword : ca_cert,
            repo_options.OPT_AUTH_CERT.keyword : cert_file,
        }

        self.server_mock.request.return_value = 201, {}

        # Test
        command = repo.RpmRepoCreateCommand(self.context)
        command.run(**data)

        # Verify
        self.assertEqual(1, self.server_mock.request.call_count)

        body = self.server_mock.request.call_args[0][2]
        body = json.loads(body)

        self.assertEqual(body['display_name'], 'Test Name')
        self.assertEqual(body['description'], 'Test Description')
        self.assertEqual(body['notes'], {'_repo-type' : 'rpm-repo', 'a' : 'a'})

        self.assertEqual(ids.TYPE_ID_IMPORTER_YUM, body['importer_type_id'])
        importer_config = body['importer_config']
        self.assertEqual(importer_config['feed_url'], 'http://localhost')
        self.assertTrue(importer_config['ssl_ca_cert'] is not None)
        self.assertTrue(importer_config['ssl_client_cert'] is not None)
        self.assertTrue(importer_config['ssl_client_key'] is not None)
        self.assertEqual(importer_config['ssl_verify'], True)
        self.assertEqual(importer_config['verify_size'], True)
        self.assertEqual(importer_config['verify_checksum'], True)
        self.assertEqual(importer_config['proxy_url'], 'http://localhost')
        self.assertEqual(importer_config['proxy_port'], 80)
        self.assertEqual(importer_config['proxy_user'], 'user')
        self.assertEqual(importer_config['proxy_pass'], 'pass')
        self.assertEqual(importer_config['max_speed'], 1024)
        self.assertEqual(importer_config['num_threads'], 8)
        self.assertEqual(importer_config['newest'], True)
        self.assertEqual(importer_config['skip'], [ids.TYPE_ID_RPM])
        self.assertEqual(importer_config['remove_old'], True)
        self.assertEqual(importer_config['num_old_packages'], 2)

        # The API will be changing to be a dict for each distributor, not a
        # list. This code will have to change to look up the parts by key
        # instead of index.

        yum_distributor = body['distributors'][0]
        self.assertEqual(ids.TYPE_ID_DISTRIBUTOR_YUM, yum_distributor['distributor_type'])
        self.assertEqual(True, yum_distributor['auto_publish'])
        self.assertEqual(ids.YUM_DISTRIBUTOR_ID, yum_distributor['distributor_id'])

        yum_config = yum_distributor['distributor_config']
        self.assertEqual(yum_config['relative_url'], '/repo')
        self.assertEqual(yum_config['http'], True)
        self.assertEqual(yum_config['https'], True)
        self.assertTrue(yum_config['gpgkey'] is not None)
        self.assertEqual(yum_config['checksum_type'], 'sha256')
        self.assertTrue(yum_config['auth_ca'] is not None)
        self.assertTrue(yum_config['auth_cert'] is not None)
        self.assertTrue(yum_config['https_ca'] is not None)
        self.assertEqual(yum_config['skip'], [ids.TYPE_ID_RPM])

        iso_distributor = body['distributors'][1]
        self.assertEqual(ids.TYPE_ID_DISTRIBUTOR_ISO, iso_distributor['distributor_id'])
        self.assertEqual(False, iso_distributor['auto_publish'])
        self.assertEqual(ids.ISO_DISTRIBUTOR_ID, iso_distributor['distributor_id'])

        iso_config = iso_distributor['distributor_config']
        self.assertEqual(iso_config['http'], True)
        self.assertEqual(iso_config['https'], True)
        self.assertTrue(iso_config['https_ca'] is not None)
        self.assertEqual(iso_config['skip'], [ids.TYPE_ID_RPM])

        self.assertEqual([TAG_SUCCESS], self.prompt.get_write_tags())


class RpmRepoUpdateCommand(rpm_support_base.PulpClientTests):

    def test_create_structure(self):
        command = repo.RpmRepoUpdateCommand(self.context)

        # Ensure the required option groups
        found_group_names = set([o.name for o in command.option_groups])
        expected_group_names = set(repo_options.ALL_GROUP_NAMES)
        self.assertEqual(found_group_names, expected_group_names)

        # Ensure the correct method is wired up
        self.assertEqual(command.method, command.run)

        # Ensure the correct metadata
        self.assertEqual(command.name, 'update')
        self.assertEqual(command.description, cudl.DESC_UPDATE)

    def test_run(self):
        # Setup
        data = {
            options.OPTION_REPO_ID.keyword : 'test-repo',
            options.OPTION_NAME.keyword : 'Test Name',
            options.OPTION_DESCRIPTION.keyword : 'Test Description',
            options.OPTION_NOTES.keyword : {'b' : 'b'},
            repo_options.OPT_FEED.keyword : 'http://localhost',
            repo_options.OPT_NEWEST.keyword : True,
            repo_options.OPT_SERVE_HTTP.keyword : True,
            repo_options.OPT_SERVE_HTTPS.keyword : True,
        }

        self.server_mock.request.return_value = 200, {}

        # Test
        command = repo.RpmRepoUpdateCommand(self.context)
        command.run(**data)

        # Verify
        self.assertEqual(1, self.server_mock.request.call_count)

        body = self.server_mock.request.call_args[0][2]
        body = json.loads(body)

        delta = body['delta']
        self.assertEqual(delta['display_name'], 'Test Name')
        self.assertEqual(delta['description'], 'Test Description')
        self.assertEqual(delta['notes'], {'b' : 'b'})

        yum_imp_config = body['importer_config']
        self.assertEqual(yum_imp_config['feed_url'], 'http://localhost')
        self.assertEqual(yum_imp_config['newest'], True)

        yum_dist_config = body['distributor_configs'][ids.YUM_DISTRIBUTOR_ID]
        self.assertEqual(yum_dist_config['http'], True)
        self.assertEqual(yum_dist_config['https'], True)
        
        iso_dist_config = body['distributor_configs'][ids.ISO_DISTRIBUTOR_ID]
        self.assertEqual(iso_dist_config['http'], True)
        self.assertEqual(iso_dist_config['https'], True)
