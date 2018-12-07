# coding=utf-8
"""Tests that perform actions over artifacts."""
import hashlib
import itertools
import unittest

from requests.exceptions import HTTPError

from pulp_smash import api, cli, config, utils
from pulp_smash.exceptions import CalledProcessError
from pulp_smash.pulp3.constants import ARTIFACTS_PATH
from pulp_smash.pulp3.utils import delete_orphans

# This import is an exception, we use a file url but we are not actually using
# any plugin
from pulpcore.tests.functional.api.using_plugin.constants import FILE_URL
from pulpcore.tests.functional.utils import set_up_module as setUpModule  # noqa:F401


class ArtifactTestCase(unittest.TestCase):
    """Create an artifact by uploading a file.

    This test targets the following issues:

    * `Pulp #2843 <https://pulp.plan.io/issues/2843>`_
    * `Pulp Smash #726 <https://github.com/PulpQE/pulp-smash/issues/726>`_
    """

    @classmethod
    def setUpClass(cls):
        """Delete orphans and create class-wide variables."""
        cfg = config.get_config()
        delete_orphans(cfg)
        cls.client = api.Client(cfg, api.json_handler)
        cls.file = {'file': utils.http_get(FILE_URL)}
        cls.file_sha256 = hashlib.sha256(cls.file['file']).hexdigest()
        cls.file_size = len(cls.file['file'])

    def test_upload_valid_attrs(self):
        """Upload a file, and provide valid attributes.

        For each possible combination of ``sha256`` and ``size`` (including
        neither), do the following:

        1. Upload a file with the chosen combination of attributes.
        2. Verify that an artifact has been created, and that it has valid
           attributes.
        3. Delete the artifact, and verify that its attributes are
           inaccessible.
        """
        file_attrs = {'sha256': self.file_sha256, 'size': self.file_size}
        for i in range(len(file_attrs) + 1):
            for keys in itertools.combinations(file_attrs, i):
                data = {key: file_attrs[key] for key in keys}
                with self.subTest(data=data):
                    self._do_upload_valid_attrs(data)

    def _do_upload_valid_attrs(self, data):
        """Upload a file with the given attributes."""
        artifact = self.client.post(ARTIFACTS_PATH, data=data, files=self.file)
        self.addCleanup(self.client.delete, artifact['_href'])
        read_artifact = self.client.get(artifact['_href'])
        for key, val in artifact.items():
            with self.subTest(key=key):
                self.assertEqual(read_artifact[key], val)
        self.doCleanups()
        with self.assertRaises(HTTPError):
            self.client.get(artifact['_href'])

    def test_upload_invalid_attrs(self):
        """Upload a file, and provide invalid attributes.

        For each possible combination of ``sha256`` and ``size`` (except for
        neither), do the following:

        1. Upload a file with the chosen combination of attributes. Verify that
           an error is returned.
        2. Verify that no artifacts exist in Pulp whose attributes match the
           file that was unsuccessfully uploaded.
        """
        file_attrs = {'sha256': utils.uuid4(), 'size': self.file_size + 1}
        for i in range(1, len(file_attrs) + 1):
            for keys in itertools.combinations(file_attrs, i):
                data = {key: file_attrs[key] for key in keys}
                with self.subTest(data=data):
                    self._do_upload_invalid_attrs(data)

    def _do_upload_invalid_attrs(self, data):
        """Upload a file with the given attributes."""
        with self.assertRaises(HTTPError):
            self.client.post(ARTIFACTS_PATH, data=data, files=self.file)
        for artifact in self.client.get(ARTIFACTS_PATH)['results']:
            self.assertNotEqual(artifact['sha256'], self.file_sha256)

    def test_upload_mixed_attrs(self):
        """Upload a file, and provide both valid and invalid attributes.

        Do the following:

        1. Upload a file and provide both an ``sha256`` and a ``size``. Let one
           be valid, and the other be valid. Verify that an error is returned.
        2. Verify that no artifacts exist in Pulp whose attributes match the
           file that was unsuccessfully uploaded.
        """
        invalid_data = (
            {'sha256': self.file_sha256, 'size': self.file_size + 1},
            {'sha256': utils.uuid4(), 'size': self.file_size}
        )
        for data in invalid_data:
            with self.subTest(data=data):
                self._do_upload_invalid_attrs(data)


class ArtifactsDeleteFileSystemTestCase(unittest.TestCase):
    """Delete an artifact, it is removed from the filesystem.

    This test targets the following issues:

    * `Pulp #3508 <https://pulp.plan.io/issues/3508>`_
    * `Pulp Smash #908 <https://github.com/PulpQE/pulp-smash/issues/908>`_
    """

    def test_all(self):
        """Delete an artifact, it is removed from the filesystem.

        Do the following:

        1. Create an artifact, and verify it is present on the filesystem.
        2. Delete the artifact, and verify it is absent on the filesystem.
        """
        cfg = config.get_config()
        api_client = api.Client(cfg, api.json_handler)
        cli_client = cli.Client(cfg)

        # create
        files = {'file': utils.http_get(FILE_URL)}
        artifact = api_client.post(ARTIFACTS_PATH, files=files)
        self.addCleanup(api_client.delete, artifact['_href'])
        cmd = ('ls', artifact['file'])
        cli_client.run(cmd, sudo=True)

        # delete
        self.doCleanups()
        with self.assertRaises(CalledProcessError):
            cli_client.run(cmd, sudo=True)
