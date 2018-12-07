# coding=utf-8
"""Tests related to repository versions."""
import unittest
from random import choice, randint, sample
from time import sleep
from urllib.parse import urlsplit

from requests.exceptions import HTTPError

from pulp_smash import api, config, utils
from pulp_smash.pulp3.constants import REPO_PATH
from pulp_smash.pulp3.utils import (
    delete_orphans,
    delete_version,
    gen_publisher,
    gen_repo,
    get_added_content,
    get_artifact_paths,
    get_content,
    get_removed_content,
    get_versions,
    publish,
    sync,
)

from pulpcore.tests.functional.api.using_plugin.constants import (
    FILE_CONTENT_PATH,
    FILE_FIXTURE_COUNT,
    FILE_FIXTURE_MANIFEST_URL,
    FILE_LARGE_FIXTURE_MANIFEST_URL,
    FILE_PUBLISHER_PATH,
    FILE_REMOTE_PATH,
)
from pulpcore.tests.functional.api.using_plugin.utils import (
    gen_file_remote,
    populate_pulp,
    skip_if,
)
from pulpcore.tests.functional.api.using_plugin.utils import set_up_module as setUpModule  # noqa:F401


class AddRemoveContentTestCase(unittest.TestCase):
    """Add and remove content to a repository. Verify side-effects.

    A new repository version is automatically created each time content is
    added to or removed from a repository. Furthermore, it's possible to
    inspect any repository version and discover which content is present, which
    content was removed, and which content was added. This test case explores
    these features.

    This test targets the following issues:

    * `Pulp #3059 <https://pulp.plan.io/issues/3059>`_
    * `Pulp #3234 <https://pulp.plan.io/issues/3234>`_
    * `Pulp Smash #878 <https://github.com/PulpQE/pulp-smash/issues/878>`_
    """

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.cfg = config.get_config()
        cls.client = api.Client(cls.cfg, api.json_handler)
        cls.remote = {}
        cls.repo = {}
        cls.content = {}

    @classmethod
    def tearDownClass(cls):
        """Destroy resources created by test methods."""
        if cls.remote:
            cls.client.delete(cls.remote['_href'])
        if cls.repo:
            cls.client.delete(cls.repo['_href'])

    def test_01_create_repository(self):
        """Create a repository.

        Assert that:

        * The ``_versions_href`` API call is correct.
        * The ``_latest_version_href`` API call is correct.
        """
        self.repo.update(self.client.post(REPO_PATH, gen_repo()))

        repo_versions = get_versions(self.repo)
        self.assertEqual(len(repo_versions), 0, repo_versions)

        self.assertIsNone(self.repo['_latest_version_href'])

    @skip_if(bool, 'repo', False)
    def test_02_sync_content(self):
        """Sync content into the repository.

        Assert that:

        * The ``_versions_href`` API call is correct.
        * The ``_latest_version_href`` API call is correct.
        * The ``_latest_version_href + content/`` API call is correct.
        * The ``_latest_version_href + added_content/`` API call is correct.
        * The ``_latest_version_href + removed_content/`` API call is correct.
        * The ``content_summary`` attribute is correct.
        """
        body = gen_file_remote()
        self.remote.update(self.client.post(FILE_REMOTE_PATH, body))
        sync(self.cfg, self.remote, self.repo)
        repo = self.client.get(self.repo['_href'])

        repo_versions = get_versions(repo)
        self.assertEqual(len(repo_versions), 1, repo_versions)

        self.assertIsNotNone(repo['_latest_version_href'])

        content = get_content(repo)
        self.assertEqual(len(content), FILE_FIXTURE_COUNT)

        added_content = get_added_content(repo)
        self.assertEqual(len(added_content), FILE_FIXTURE_COUNT, added_content)

        removed_content = get_removed_content(repo)
        self.assertEqual(len(removed_content), 0, removed_content)

        content_summary = self.get_content_summary(repo)
        self.assertEqual(content_summary, {'file': FILE_FIXTURE_COUNT})

    @skip_if(bool, 'repo', False)
    def test_03_remove_content(self):
        """Remove content from the repository.

        Make roughly the same assertions as :meth:`test_02_sync_content`.
        """
        repo = self.client.get(self.repo['_href'])
        self.content.update(choice(get_content(repo)))
        self.client.post(
            repo['_versions_href'],
            {'remove_content_units': [self.content['_href']]}
        )
        repo = self.client.get(self.repo['_href'])

        repo_versions = get_versions(repo)
        self.assertEqual(len(repo_versions), 2, repo_versions)

        self.assertIsNotNone(repo['_latest_version_href'])

        content = get_content(repo)
        self.assertEqual(len(content), FILE_FIXTURE_COUNT - 1)

        added_content = get_added_content(repo)
        self.assertEqual(len(added_content), 0, added_content)

        removed_content = get_removed_content(repo)
        self.assertEqual(len(removed_content), 1, removed_content)

        content_summary = self.get_content_summary(repo)
        self.assertEqual(content_summary, {'file': FILE_FIXTURE_COUNT - 1})

    @skip_if(bool, 'repo', False)
    def test_04_add_content(self):
        """Add content to the repository.

        Make roughly the same assertions as :meth:`test_02_sync_content`.
        """
        repo = self.client.get(self.repo['_href'])
        self.client.post(
            repo['_versions_href'],
            {'add_content_units': [self.content['_href']]}
        )
        repo = self.client.get(self.repo['_href'])

        repo_versions = get_versions(repo)
        self.assertEqual(len(repo_versions), 3, repo_versions)

        self.assertIsNotNone(repo['_latest_version_href'])

        content = get_content(repo)
        self.assertEqual(len(content), FILE_FIXTURE_COUNT)

        added_content = get_added_content(repo)
        self.assertEqual(len(added_content), 1, added_content)

        removed_content = get_removed_content(repo)
        self.assertEqual(len(removed_content), 0, removed_content)

        content_summary = self.get_content_summary(repo)
        self.assertEqual(content_summary, {'file': FILE_FIXTURE_COUNT})

    def get_content_summary(self, repo):
        """Get the ``content_summary`` for the given repository."""
        repo_versions = get_versions(repo)
        content_summaries = [
            repo_version['content_summary']
            for repo_version in repo_versions
            if repo_version['_href'] == repo['_latest_version_href']
        ]
        self.assertEqual(len(content_summaries), 1, content_summaries)
        return content_summaries[0]


class SyncChangeRepoVersionTestCase(unittest.TestCase):
    """Verify whether sync of repository updates repository version."""

    def test_all(self):
        """Verify whether the sync of a repository updates its version.

        This test explores the design choice stated in the `Pulp #3308`_ that a
        new repository version is created even if the sync does not add or
        remove any content units. Even without any changes to the remote if a
        new sync occurs, a new repository version is created.

        .. _Pulp #3308: https://pulp.plan.io/issues/3308

        Do the following:

        1. Create a repository, and a remote.
        2. Sync the repository an arbitrary number of times.
        3. Verify that the repository version is equal to the previous number
           of syncs.
        """
        cfg = config.get_config()
        client = api.Client(cfg, api.json_handler)

        repo = client.post(REPO_PATH, gen_repo())
        self.addCleanup(client.delete, repo['_href'])

        body = gen_file_remote()
        remote = client.post(FILE_REMOTE_PATH, body)
        self.addCleanup(client.delete, remote['_href'])

        number_of_syncs = randint(1, 10)
        for _ in range(number_of_syncs):
            sync(cfg, remote, repo)

        repo = client.get(repo['_href'])
        path = urlsplit(repo['_latest_version_href']).path
        latest_repo_version = int(path.split('/')[-2])
        self.assertEqual(latest_repo_version, number_of_syncs)


class AddRemoveRepoVersionTestCase(unittest.TestCase):
    """Create and delete repository versions.

    This test targets the following issues:

    * `Pulp #3219 <https://pulp.plan.io/issues/3219>`_
    * `Pulp Smash #871 <https://github.com/PulpQE/pulp-smash/issues/871>`_
    """

    # `cls.content[i]` is a dict.
    # pylint:disable=unsubscriptable-object

    @classmethod
    def setUpClass(cls):
        """Add content to Pulp."""
        cls.cfg = config.get_config()
        cls.client = api.Client(cls.cfg, api.json_handler)
        populate_pulp(cls.cfg, url=FILE_LARGE_FIXTURE_MANIFEST_URL)
        # We need at least three content units. Choosing a relatively low
        # number is useful, to limit how many repo versions are created, and
        # thus how long the test takes.
        cls.content = sample(cls.client.get(FILE_CONTENT_PATH)['results'], 10)

    def setUp(self):
        """Create a repository and give it nine new versions."""
        self.repo = self.client.post(REPO_PATH, gen_repo())
        self.addCleanup(self.client.delete, self.repo['_href'])

        # Don't upload the last content unit. The test case might upload it to
        # create a new repo version within the test.
        for content in self.content[:-1]:
            self.client.post(
                self.repo['_versions_href'],
                {'add_content_units': [content['_href']]}
            )
        self.repo = self.client.get(self.repo['_href'])
        self.repo_version_hrefs = tuple(
            version['_href'] for version in get_versions(self.repo)
        )

    def test_delete_first_version(self):
        """Delete the first repository version."""
        delete_version(self.repo, self.repo_version_hrefs[0])
        with self.assertRaises(HTTPError):
            get_content(self.repo, self.repo_version_hrefs[0])
        for repo_version_href in self.repo_version_hrefs[1:]:
            artifact_paths = get_artifact_paths(self.repo, repo_version_href)
            self.assertIn(self.content[0]['artifact'], artifact_paths)

    def test_delete_last_version(self):
        """Delete the last repository version.

        Create a new repository version from the second-to-last repository
        version. Verify that the content unit from the old last repository
        version is not in the new last repository version.
        """
        # Delete the last repo version.
        delete_version(self.repo, self.repo_version_hrefs[-1])
        with self.assertRaises(HTTPError):
            get_content(self.repo, self.repo_version_hrefs[-1])

        # Make new repo version from new last repo version.
        self.client.post(
            self.repo['_versions_href'],
            {'add_content_units': [self.content[-1]['_href']]}
        )
        self.repo = self.client.get(self.repo['_href'])
        artifact_paths = get_artifact_paths(self.repo)

        self.assertNotIn(self.content[-2]['artifact'], artifact_paths)
        self.assertIn(self.content[-1]['artifact'], artifact_paths)

    def test_delete_middle_version(self):
        """Delete a middle version."""
        index = randint(1, len(self.repo_version_hrefs) - 2)
        delete_version(self.repo, self.repo_version_hrefs[index])

        with self.assertRaises(HTTPError):
            get_content(self.repo, self.repo_version_hrefs[index])

        for repo_version_href in self.repo_version_hrefs[index + 1:]:
            artifact_paths = get_artifact_paths(self.repo, repo_version_href)
            self.assertIn(self.content[index]['artifact'], artifact_paths)

    def test_delete_publication(self):
        """Delete a publication.

        Delete a repository version, and verify the associated publication is
        also deleted.
        """
        publisher = self.client.post(FILE_PUBLISHER_PATH, gen_publisher())
        self.addCleanup(self.client.delete, publisher['_href'])

        publication = publish(self.cfg, publisher, self.repo)
        delete_version(self.repo)

        with self.assertRaises(HTTPError):
            self.client.get(publication['_href'])


class ContentImmutableRepoVersionTestCase(unittest.TestCase):
    """Test whether the content present in a repo version is immutable.

    This test targets the following issue:

    * `Pulp Smash #953 <https://github.com/PulpQE/pulp-smash/issues/953>`_
    """

    def test_all(self):
        """Test whether the content present in a repo version is immutable.

        Do the following:

        1. Create a repository that has at least one repository version.
        2. Attempt to update the content of a repository version.
        3. Assert that an HTTP exception is raised.
        4. Assert that the repository version was not updated.
        """
        cfg = config.get_config()
        client = api.Client(cfg, api.json_handler)

        repo = client.post(REPO_PATH, gen_repo())
        self.addCleanup(client.delete, repo['_href'])

        body = gen_file_remote()
        remote = client.post(FILE_REMOTE_PATH, body)
        self.addCleanup(client.delete, remote['_href'])

        sync(cfg, remote, repo)

        latest_version_href = client.get(repo['_href'])['_latest_version_href']
        with self.assertRaises(HTTPError):
            client.post(latest_version_href)
        repo = client.get(repo['_href'])
        self.assertEqual(latest_version_href, repo['_latest_version_href'])


class FilterRepoVersionTestCase(unittest.TestCase):
    """Test whether repository versions can be filtered.

    These tests target the following issues:

    * `Pulp #3238 <https://pulp.plan.io/issues/3238>`_
    * `Pulp #3536 <https://pulp.plan.io/issues/3536>`_
    * `Pulp #3557 <https://pulp.plan.io/issues/3557>`_
    * `Pulp #3558 <https://pulp.plan.io/issues/3558>`_
    * `Pulp Smash #880 <https://github.com/PulpQE/pulp-smash/issues/880>`_
    """

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables.

        Add content to Pulp.
        """
        cls.cfg = config.get_config()
        cls.client = api.Client(cls.cfg, api.json_handler)

        populate_pulp(cls.cfg)
        cls.contents = cls.client.get(FILE_CONTENT_PATH)['results']

    def setUp(self):
        """Create a repository and give it new versions."""
        self.repo = self.client.post(REPO_PATH, gen_repo())
        self.addCleanup(self.client.delete, self.repo['_href'])

        for content in self.contents[:10]:  # slice is arbitrary upper bound
            self.client.post(
                self.repo['_versions_href'],
                {'add_content_units': [content['_href']]}
            )
            sleep(1)
        self.repo = self.client.get(self.repo['_href'])

    def test_filter_invalid_content(self):
        """Filter repository version by invalid content."""
        with self.assertRaises(HTTPError):
            get_versions(self.repo, {'content': utils.uuid4()})

    def test_filter_valid_content(self):
        """Filter repository versions by valid content."""
        content = choice(self.contents)
        repo_versions = get_versions(self.repo, {'content': content['_href']})
        for repo_version in repo_versions:
            self.assertIn(
                self.client.get(content['_href']),
                get_content(self.repo, repo_version['_href'])
            )

    def test_filter_invalid_date(self):
        """Filter repository version by invalid date."""
        criteria = utils.uuid4()
        for params in (
                {'created': criteria},
                {'created__gt': criteria, 'created__lt': criteria},
                {'created__gte': criteria, 'created__lte': criteria},
                {'created__range': ','.join((criteria, criteria))}):
            with self.subTest(params=params):
                with self.assertRaises(HTTPError):
                    get_versions(self.repo, params)

    def test_filter_valid_date(self):
        """Filter repository version by a valid date."""
        dates = self.get_repo_versions_attr('created')
        for params, num_results in (
                ({'created': dates[0]},
                 1),
                ({'created__gt': dates[0], 'created__lt': dates[-1]},
                 len(dates) - 2),
                ({'created__gte': dates[0], 'created__lte': dates[-1]},
                 len(dates)),
                ({'created__range': ','.join((dates[0], dates[1]))},
                 2)):
            with self.subTest(params=params):
                results = get_versions(self.repo, params)
                self.assertEqual(len(results), num_results, results)

    def test_filter_nonexistent_version(self):
        """Filter repository version by a nonexistent version number."""
        criteria = -1
        for params in (
                {'number': criteria},
                {'number__gt': criteria, 'number__lt': criteria},
                {'number__gte': criteria, 'number__lte': criteria},
                {'number__range': ','.join((str(criteria), str(criteria)))}):
            with self.subTest(params=params):
                versions = get_versions(self.repo, params)
                self.assertEqual(len(versions), 0, versions)

    def test_filter_invalid_version(self):
        """Filter repository version by an invalid version number."""
        criteria = utils.uuid4()
        for params in (
                {'number': criteria},
                {'number__gt': criteria, 'number__lt': criteria},
                {'number__gte': criteria, 'number__lte': criteria},
                {'number__range': ','.join((criteria, criteria))}):
            with self.subTest(params=params):
                with self.assertRaises(HTTPError):
                    get_versions(self.repo, params)

    def test_filter_valid_version(self):
        """Filter repository version by a valid version number."""
        numbers = self.get_repo_versions_attr('number')
        for params, num_results in (
                ({'number': numbers[0]},
                 1),
                ({'number__gt': numbers[0], 'number__lt': numbers[-1]},
                 len(numbers) - 2),
                ({'number__gte': numbers[0], 'number__lte': numbers[-1]},
                 len(numbers)),
                ({'number__range': '{},{}'.format(numbers[0], numbers[1])},
                 2)):
            with self.subTest(params=params):
                results = get_versions(self.repo, params)
                self.assertEqual(len(results), num_results, results)

    def test_deleted_version_filter(self):
        """Delete a repository version and filter by its number."""
        numbers = self.get_repo_versions_attr('number')
        delete_version(self.repo)
        versions = get_versions(self.repo, {'number': numbers[-1]})
        self.assertEqual(len(versions), 0, versions)

    def get_repo_versions_attr(self, attr):
        """Get an ``attr`` about each version of ``self.repo``.

        Return as sorted list.
        """
        attributes = [version[attr] for version in get_versions(self.repo)]
        attributes.sort()
        return attributes


class CreatedResourcesTaskTestCase(unittest.TestCase):
    """Verify whether task report shows that a repository version was created.

    This test targets the following issue:

    `Pulp Smash #876 <https://github.com/PulpQE/pulp-smash/issues/876>`_.
    """

    def test_all(self):
        """Verify whether task report shows repository version was created."""
        cfg = config.get_config()
        client = api.Client(cfg, api.json_handler)
        repo = client.post(REPO_PATH, gen_repo())
        self.addCleanup(client.delete, repo['_href'])
        body = gen_file_remote()
        remote = client.post(FILE_REMOTE_PATH, body)
        self.addCleanup(client.delete, remote['_href'])
        call_report = sync(cfg, remote, repo)
        last_task = next(api.poll_spawned_tasks(cfg, call_report))
        for key in ('repositories', 'versions'):
            self.assertIn(
                key,
                last_task['created_resources'][0],
                last_task['created_resources']
            )


class CreateRepoBaseVersionTestCase(unittest.TestCase):
    """Test whether one can create a repository version from any version.

    This test targets the following issues:

    `Pulp #3360 <https://pulp.plan.io/issues/3360>`_
    `Pulp #4035 <https://pulp.plan.io/issues/4035>`_
    """

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.cfg = config.get_config()
        delete_orphans(cls.cfg)
        populate_pulp(cls.cfg, url=FILE_LARGE_FIXTURE_MANIFEST_URL)
        cls.client = api.Client(cls.cfg, api.page_handler)
        cls.content = cls.client.get(FILE_CONTENT_PATH)

    def test_same_repository(self):
        """Test ``base_version`` for the same repository.

        Do the following:

        1. Create a repository.
        2. Sync the repository (this creates repository version 1).
        3. Add a new content unit a new repository version (this create
           repository version 2).
        4. Create a new repository version using version 1 as ``base_version``
           (this creates version 3).
        5. Check that version 1 and version 3 have the same content.
        """
        # create repo version 1
        repo = self.create_sync_repo()
        version_content = []
        version_content.append(
            sorted(
                [self.remove_created_key(item) for item in get_content(repo)],
                key=lambda item: item['_href'],
            )
        )
        self.assertIsNone(get_versions(repo)[0]['base_version'])

        content = self.content.pop()

        # create repo version 2
        self.client.post(
            repo['_versions_href'],
            {'add_content_units': [content['_href']]}
        )
        repo = self.client.get(repo['_href'])

        # create repo version 3 from version 1
        base_version = get_versions(repo)[0]['_href']
        self.client.post(
            repo['_versions_href'],
            {'base_version': base_version}
        )
        repo = self.client.get(repo['_href'])

        # assert that base_version of the version 3 points to version 1
        self.assertEqual(get_versions(repo)[2]['base_version'], base_version)

        # assert that content on version 1 is equal to content on version 3
        version_content.append(
            sorted(
                [self.remove_created_key(item) for item in get_content(repo)],
                key=lambda item: item['_href'],
            )
        )
        self.assertEqual(
            version_content[0],
            version_content[1],
            version_content
        )

    def test_different_repository(self):
        """Test ``base_version`` for different repositories.

        Do the following:

        1. Create a new repository A and sync it.
        2. Create a new repository B and a new version for this repository
           specify repository A version 1 as the ``base_version``.
        3. Check that repository A version 1 and repository B version 1 have
           the same content.
        """
        # create repo A
        repo = self.create_sync_repo()
        version_content = []
        version_content.append(
            sorted(
                [self.remove_created_key(item) for item in get_content(repo)],
                key=lambda item: item['_href'],
            )
        )
        self.assertIsNone(get_versions(repo)[0]['base_version'])

        # get repo A version 1 to be used as base_version
        base_version = get_versions(repo)[0]['_href']

        # create repo B
        repo = self.client.post(REPO_PATH, gen_repo())
        self.addCleanup(self.client.delete, repo['_href'])

        # create a version for repo B using repo A version 1 as base_version
        self.client.post(
            repo['_versions_href'],
            {'base_version': base_version}
        )
        repo = self.client.get(repo['_href'])

        # assert that base_version of repo B points to version 1 of repo A
        self.assertEqual(get_versions(repo)[0]['base_version'], base_version)

        # assert that content on version 1 of repo A is equal to content on
        # version 1 repo B
        version_content.append(
            sorted(
                [self.remove_created_key(item) for item in get_content(repo)],
                key=lambda item: item['_href'],
            )
        )

        self.assertEqual(
            version_content[0],
            version_content[1],
            version_content
        )

    def test_base_version_other_parameters(self):
        """Test ``base_version`` can be used together with other parameters.

        ``add_content_units`` and ``remove_content_units``.
        """
        # create repo version 1
        repo = self.create_sync_repo()
        version_1_content = [
            self.remove_created_key(item) for item in get_content(repo)
        ]
        self.assertIsNone(get_versions(repo)[0]['base_version'])

        # create repo version 2 from version 1
        base_version = get_versions(repo)[0]['_href']
        added_content = self.remove_created_key(self.content.pop())
        removed_content = choice(version_1_content)
        self.client.post(
            repo['_versions_href'],
            {
                'base_version': base_version,
                'add_content_units': [added_content['_href']],
                'remove_content_units': [removed_content['_href']]
            }
        )
        repo = self.client.get(repo['_href'])
        version_2_content = [
            self.remove_created_key(item) for item in get_content(repo)
        ]

        # assert that base_version of the version 2 points to version 1
        self.assertEqual(get_versions(repo)[1]['base_version'], base_version)

        # assert that the removed content is not present on repo version 2
        self.assertNotIn(removed_content, version_2_content)

        # assert that the added content is present on repo version 2
        self.assertIn(added_content, version_2_content)

        # assert that the same amount of units are present in both versions
        self.assertEqual(len(version_1_content), len(version_2_content))

    def test_base_version_exception(self):
        """Exception is raised when non-existent ``base_version`` is used.

        Do the following:

        1. Create a repository B and an attempt to specify a non-existent
           ``base_version``.
        3. Assert that an HTTP exception is raised.
        """
        repo = self.client.post(REPO_PATH, gen_repo())
        self.addCleanup(self.client.delete, repo['_href'])

        with self.assertRaises(HTTPError):
            self.client.post(
                repo['_versions_href'],
                {'base_version': utils.uuid4()}
            )

    def create_sync_repo(self):
        """Create, and sync a repo."""
        repo = self.client.post(REPO_PATH, gen_repo())
        self.addCleanup(self.client.delete, repo['_href'])
        body = gen_file_remote(url=FILE_FIXTURE_MANIFEST_URL)
        remote = self.client.post(FILE_REMOTE_PATH, body)
        self.addCleanup(self.client.delete, remote['_href'])
        sync(self.cfg, remote, repo)
        return self.client.get(repo['_href'])

    @staticmethod
    def remove_created_key(dic):
        """Given a dict remove the key `created`."""
        return {k: v for k, v in dic.items() if k != 'created'}
