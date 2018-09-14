# coding=utf-8
"""Tests related to the tasking system."""
import unittest

from pulp_smash import api, config
from pulp_smash.pulp3.constants import REPO_PATH
from pulp_smash.pulp3.utils import (
    gen_repo,
    get_content,
    sync,
)

from tests.functional.api.using_plugin.constants import (
    FILE_FIXTURE_MANIFEST_URL,
    FILE_FIXTURE_COUNT,
    FILE_LARGE_FIXTURE_MANIFEST_URL,
    FILE_REMOTE_PATH,
)
from tests.functional.api.using_plugin.utils import gen_file_remote
from tests.functional.api.using_plugin.utils import set_up_module as setUpModule  # noqa:F401


class MultiResourceLockingTestCase(unittest.TestCase):
    """Verify multi-resourcing locking.

    This test targets the following issues:

    * `Pulp #3186 <https://pulp.plan.io/issues/3186>`_
    * `Pulp Smash #879 <https://github.com/PulpQE/pulp-smash/issues/879>`_
    """

    def test_all(self):
        """Verify multi-resourcing locking.

        Do the following:

        1. Create a repository, and a remote.
        2. Update the remote to point to a different url.
        3. Immediately run a sync. The sync should fire after the update and
           sync from the second url.
        4. Assert that remote url was updated.
        5. Assert that the number of units present in the repository is
           according to the updated url.
        """
        cfg = config.get_config()
        client = api.Client(cfg, api.json_handler)

        repo = client.post(REPO_PATH, gen_repo())
        self.addCleanup(client.delete, repo['_href'])

        body = gen_file_remote(url=FILE_LARGE_FIXTURE_MANIFEST_URL)
        remote = client.post(FILE_REMOTE_PATH, body)
        self.addCleanup(client.delete, remote['_href'])

        url = {'url': FILE_FIXTURE_MANIFEST_URL}
        client.patch(remote['_href'], url)

        sync(cfg, remote, repo)

        repo = client.get(repo['_href'])
        remote = client.get(remote['_href'])
        self.assertEqual(remote['url'], url['url'])
        self.assertEqual(len(get_content(repo)), FILE_FIXTURE_COUNT)
