"""
This module contains functional tests for the 23rd migration.
"""
import os
import shutil
import stat
import tempfile
import unittest

import mock

from pulp.server.db import connection
from pulp.server.db.migrate.models import _import_all_the_way


migration = _import_all_the_way('pulp.server.db.migrations.0023_importer_tls_storage')


class TestMigrate(unittest.TestCase):
    def tearDown(self):
        """
        Remove any database objects that were created during the test.
        """
        connection._DATABASE.repo_importers.remove()

    def test_LOCAL_STORAGE(self):
        """
        Assert that the LOCAL_STORAGE variable is correct.
        """
        self.assertEqual(migration.LOCAL_STORAGE, '/var/lib/pulp')

    def test_migrate_with_one_cert(self):
        """
        Ensure that the migrate() function operates correctly where there are two Importers and only
        one has a cert.
        """
        # The first importer does not have any certs or keys, so only the second should get written
        # to storage.
        importers = [
            {"repo_id": "repo_1", "importer_type_id": "supercar",
             "config": {},
             "_ns": "repo_importers"},
            {"repo_id": "repo_2", "importer_type_id": "supercar",
             "config": {
                 "ssl_ca_cert": "CA Cert 2", "ssl_client_cert": "Client Cert 2",
                 "ssl_client_key": "Client Key 2"},
             "_ns": "repo_importers"}]
        temp_path = tempfile.mkdtemp()
        try:
            with mock.patch('pulp.server.db.migrations.0023_importer_tls_storage.LOCAL_STORAGE',
                            temp_path):
                # Write the importers using pymongo to isolate our tests from any future changes
                # that might happen to the mongoengine models.
                connection._DATABASE.repo_importers.insert(importers)

                # This should write the documents to the correct locations.
                migration.migrate()

                # First, assert that only one importer's folder was created.
                self.assertEqual(os.listdir(os.path.join(temp_path, 'importers')),
                                 ['repo_2-supercar'])

                # The rest of our assertions will check that the second importer's certs were
                # written correctly. Begin by asserting that the pki_path was created with the
                # correct permissions (0700).
                pki_stat = os.stat(
                    self._expected_pki_path(temp_path, 'repo_2', 'supercar'))
                self.assertEqual(pki_stat[stat.ST_MODE], stat.S_IFDIR | stat.S_IRWXU)

                ca_path = os.path.join(
                    self._expected_pki_path(temp_path, 'repo_2', 'supercar'),
                    'ca.crt')
                client_cert_path = os.path.join(
                    self._expected_pki_path(temp_path, 'repo_2', 'supercar'),
                    'client.crt')
                client_key_path = os.path.join(
                    self._expected_pki_path(temp_path, 'repo_2', 'supercar'),
                    'client.key')

                # Ensure that the correct contents were written to each file.
                with open(ca_path) as ca_file:
                    self.assertEqual(ca_file.read(), 'CA Cert 2')
                with open(client_cert_path) as client_cert_file:
                    self.assertEqual(client_cert_file.read(), 'Client Cert 2')
                with open(client_key_path) as client_key_file:
                    self.assertEqual(client_key_file.read(), 'Client Key 2')

                # Assert that each path is a regular file, and that the permissions are
                # set to 0600
                for path in [ca_path, client_cert_path, client_key_path]:
                    self.assertEqual(os.stat(path)[stat.ST_MODE],
                                     stat.S_IFREG | stat.S_IRUSR | stat.S_IWUSR)
        finally:
            shutil.rmtree(temp_path)

    def test_migrate_with_two_certs(self):
        """
        Ensure that the migrate() function operates correctly where there are two Importers and they
        both have certs.
        """
        importers = [
            {"repo_id": "repo_1", "importer_type_id": "supercar",
             "config": {
                 "ssl_ca_cert": "CA Cert 1", "ssl_client_cert": "Client Cert 1",
                 "ssl_client_key": "Client Key 1"},
             "_ns": "repo_importers"},
            {"repo_id": "repo_2", "importer_type_id": "supercar",
             "config": {
                 "ssl_ca_cert": "CA Cert 2", "ssl_client_cert": "Client Cert 2",
                 "ssl_client_key": "Client Key 2"},
             "_ns": "repo_importers"}]
        temp_path = tempfile.mkdtemp()
        try:
            with mock.patch('pulp.server.db.migrations.0023_importer_tls_storage.LOCAL_STORAGE',
                            temp_path):
                # Write the importers using pymongo to isolate our tests from any future changes
                # that might happen to the mongoengine models.
                connection._DATABASE.repo_importers.insert(importers)

                # This should write the documents to the correct locations.
                migration.migrate()

                # Assert that both importers' data was written correctly.
                for i in range(1, 3):
                    # Assert that the pki_path was created with the correct permissions (0700).
                    pki_stat = os.stat(
                        self._expected_pki_path(temp_path, 'repo_{0}'.format(i), 'supercar'))
                    self.assertEqual(pki_stat[stat.ST_MODE], stat.S_IFDIR | stat.S_IRWXU)

                    ca_path = os.path.join(
                        self._expected_pki_path(temp_path, 'repo_{0}'.format(i), 'supercar'),
                        'ca.crt')
                    client_cert_path = os.path.join(
                        self._expected_pki_path(temp_path, 'repo_{0}'.format(i), 'supercar'),
                        'client.crt')
                    client_key_path = os.path.join(
                        self._expected_pki_path(temp_path, 'repo_{0}'.format(i), 'supercar'),
                        'client.key')

                    # Ensure that the correct contents were written to each file.
                    with open(ca_path) as ca_file:
                        self.assertEqual(ca_file.read(), 'CA Cert {0}'.format(i))
                    with open(client_cert_path) as client_cert_file:
                        self.assertEqual(client_cert_file.read(), 'Client Cert {0}'.format(i))
                    with open(client_key_path) as client_key_file:
                        self.assertEqual(client_key_file.read(), 'Client Key {0}'.format(i))

                    # Assert that each path is a regular file, and that the permissions are
                    # set to 0600
                    for path in [ca_path, client_cert_path, client_key_path]:
                        self.assertEqual(os.stat(path)[stat.ST_MODE],
                                         stat.S_IFREG | stat.S_IRUSR | stat.S_IWUSR)
        finally:
            shutil.rmtree(temp_path)

    def test_migrate_without_certs(self):
        """
        Test migrate() when there are no certs.
        """
        # The first importer does not have any certs or keys. The second has the config keys for
        # the certs and key, but they are all empty strings. Neither of them should be written to
        # disk.
        importers = [
            {"repo_id": "repo_1", "importer_type_id": "supercar",
             "config": {},
             "_ns": "repo_importers"},
            {"repo_id": "repo_2", "importer_type_id": "supercar",
             "config": {"ssl_ca_cert": "", "ssl_client_cert": "", "ssl_client_key": ""},
             "_ns": "repo_importers"}]
        temp_path = tempfile.mkdtemp()
        try:
            with mock.patch('pulp.server.db.model.LOCAL_STORAGE', temp_path):
                # Write the importers using pymongo to isolate our tests from any future changes
                # that might happen to the mongoengine models.
                connection._DATABASE.repo_importers.insert(importers)

                # This should write the documents to the correct locations.
                migration.migrate()

                # Assert that neither importer's folder was created.
                self.assertEqual(os.listdir(temp_path), [])
        finally:
            shutil.rmtree(temp_path)

    @staticmethod
    def _expected_pki_path(local_storage_path, repo_id, importer_type_id):
        """
        Return the expected pki path for a given repo/importer combo.
        """
        return os.path.join(local_storage_path, 'importers',
                            '{0}-{1}'.format(repo_id, importer_type_id), 'pki')
