from os import readlink
import copy
import csv
import errno
import os
import shutil
import tempfile
import unittest

from mock import Mock, MagicMock, patch

from pulp.common.plugins.distributor_constants import MANIFEST_FILENAME
from pulp.devel.mock_distributor import get_publish_conduit
from pulp.plugins.file.distributor import FileDistributor, FilePublishProgressReport, BUILD_DIRNAME
from pulp.plugins.model import Repository, Unit
from pulp.plugins.config import PluginCallConfiguration


DATA_DIR = os.path.realpath("../../../data/")
SAMPLE_RPM = 'pulp-test-package-0.3.1-1.fc11.x86_64.rpm'
SAMPLE_FILE = 'test-override-pulp.conf'


class FileDistributorTest(unittest.TestCase):
    """
    Tests the file distributor base class
    """
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

        self.target_dir = os.path.join(self.temp_dir, "target")
        self.repo = MagicMock(spec=Repository)
        self.repo.id = "foo"
        self.repo.working_dir = self.temp_dir
        self.unit = Unit('RPM', {'name': SAMPLE_RPM, 'size': 1, 'checksum': 'sum1'}, {},
                         os.path.join(DATA_DIR, SAMPLE_RPM))
        self.publish_conduit = get_publish_conduit(existing_units=[self.unit, ])

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def create_distributor_with_mocked_api_calls(self):
        distributor = FileDistributor()
        distributor.get_hosting_locations = Mock()
        distributor.get_hosting_locations.return_value = [self.target_dir, ]
        distributor.post_repo_publish = Mock()
        return distributor

    def test_metadata_not_implemented(self):
        self.assertRaises(NotImplementedError, FileDistributor.metadata)

    def test_validate_config_not_implemented(self):
        distributor = FileDistributor()
        self.assertRaises(NotImplementedError, distributor.validate_config, None, None, None)

    def test_get_hosting_locations_not_implemented(self):
        distributor = FileDistributor()
        host_locations = distributor.get_hosting_locations(None, None)
        self.assertEquals(0, len(host_locations))

    def test_post_repo_publish_not_implemented(self):
        distributor = FileDistributor()
        # ensure that this doesn't raise an error
        distributor.post_repo_publish(None, None)

    @patch('pulp.server.managers.repo._common.get_working_directory', spec_set=True)
    def test_repo_publish_api_calls(self, mock_get_working, force_full=True):
        mock_get_working.return_value = self.temp_dir
        distributor = self.create_distributor_with_mocked_api_calls()
        config = PluginCallConfiguration({}, {}, {'force_full': force_full})
        result = distributor.publish_repo(self.repo, self.publish_conduit, config)
        self.assertTrue(result.success_flag)
        self.assertTrue(distributor.get_hosting_locations.called)
        self.assertTrue(distributor.post_repo_publish.called)

        # The publish_conduit should have had two set_progress calls. One to start the IN_PROGRESS
        # state, and the second to mark it as complete
        self.assertEqual(self.publish_conduit.set_progress.call_count, 2)
        self.assertEqual(self.publish_conduit.set_progress.mock_calls[0][1][0]['state'],
                         FilePublishProgressReport.STATE_IN_PROGRESS)
        self.assertEqual(self.publish_conduit.set_progress.mock_calls[1][1][0]['state'],
                         FilePublishProgressReport.STATE_COMPLETE)

    @patch('pulp.server.managers.repo._common.get_working_directory', spec_set=True)
    def test_repo_publish_files_placed_properly(self, mock_get_working, force_full=True):
        mock_get_working.return_value = self.temp_dir
        distributor = self.create_distributor_with_mocked_api_calls()
        config = PluginCallConfiguration({}, {}, {'force_full': force_full})
        distributor.publish_repo(self.repo, self.publish_conduit, config)
        target_file = os.path.join(self.target_dir, SAMPLE_RPM)
        # test if the link was created
        self.assertTrue(os.path.islink(target_file))
        # test if the link points to the correct place
        link_target = os.readlink(target_file)
        self.assertEquals(link_target, os.path.join(DATA_DIR, SAMPLE_RPM))

    @patch('pulp.server.managers.repo._common.get_working_directory', spec_set=True)
    def test_repo_publish_metadata_writing(self, mock_get_working, force_full=True):
        mock_get_working.return_value = self.temp_dir
        distributor = self.create_distributor_with_mocked_api_calls()
        config = PluginCallConfiguration({}, {}, {'force_full': force_full})
        distributor.publish_repo(self.repo, self.publish_conduit, config)
        with open(os.path.join(self.target_dir, MANIFEST_FILENAME), 'rb') as f:
            reader = csv.reader(f)
            row = reader.next()
            self.assertEquals(row[0], self.unit.unit_key['name'])
            self.assertEquals(row[1], self.unit.unit_key['checksum'])
            self.assertEquals(row[2], str(self.unit.unit_key['size']))

    @patch('pulp.server.managers.repo._common.get_working_directory', spec_set=True)
    @patch('pulp.plugins.file.distributor._logger')
    def test_repo_publish_handles_errors(self, mock_logger, mock_get_working, force_full=True):
        """
        Make sure that publish() does the right thing with the report when there is an error.
        """
        mock_get_working.return_value = self.temp_dir
        distributor = self.create_distributor_with_mocked_api_calls()

        distributor.post_repo_publish.side_effect = Exception('Rawr!')
        config = PluginCallConfiguration({}, {}, {'force_full': force_full})
        report = distributor.publish_repo(self.repo, self.publish_conduit, config)

        self.assertTrue(mock_logger.exception.called)

        self.assertFalse(report.success_flag)
        self.assertEqual(report.summary['state'], FilePublishProgressReport.STATE_FAILED)
        self.assertEqual(report.summary['error_message'], 'Rawr!')
        self.assertTrue('Rawr!' in report.summary['traceback'])

        # The publish_conduit should have had two set_progress calls. One to start the IN_PROGRESS
        # state, and the second to mark it as failed
        self.assertEqual(self.publish_conduit.set_progress.call_count, 2)
        self.assertEqual(self.publish_conduit.set_progress.mock_calls[0][1][0]['state'],
                         FilePublishProgressReport.STATE_IN_PROGRESS)
        self.assertEqual(self.publish_conduit.set_progress.mock_calls[1][1][0]['state'],
                         FilePublishProgressReport.STATE_FAILED)

    @patch('pulp.server.managers.repo._common.get_working_directory', spec_set=True)
    def test_republish_after_unit_removal(self, mock_get_working, force_full=True):
        """
        This test checks for an issue[0] we had where publishing an ISO repository, removing an ISO,
        and then republishing would leave that removed ISO's symlink in the repository even though
        it had been removed from the manifest. This test asserts that the republished repository no
        longer contains the removed ISO.

        [0] https://bugzilla.redhat.com/show_bug.cgi?id=970795

        :param delete_protected_repo: The mocked version of delete_protected_repo
        :type  delete_protected_repo: function
        """
        mock_get_working.return_value = self.temp_dir
        # Publish a repository
        distributor = self.create_distributor_with_mocked_api_calls()
        config = PluginCallConfiguration({}, {}, {'force_full': force_full})
        distributor.publish_repo(self.repo, self.publish_conduit, config)
        target_file = os.path.join(self.target_dir, SAMPLE_RPM)
        # test if the link was created
        self.assertTrue(os.path.islink(target_file))

        # publish a new repo with a different unit in it
        cloned_unit = copy.deepcopy(self.unit)
        cloned_unit.unit_key['name'] = 'foo.rpm'
        cloned_unit.unit_key['checksum'] = 'sum2'
        new_conduit = get_publish_conduit(existing_units=[cloned_unit, ])
        distributor.publish_repo(self.repo, new_conduit, PluginCallConfiguration({}, {}, {}))
        # Make sure the new rpm is linked
        self.assertTrue(os.path.islink(os.path.join(self.target_dir, 'foo.rpm')))
        # Ensure the old rpm is no longer included
        self.assertFalse(os.path.islink(target_file))
        # Ensure PULP_MANIFEST is updated correctly
        with open(os.path.join(self.target_dir, MANIFEST_FILENAME), 'r') as f:
            self.assertEqual(len(f.readlines()), 1)
        with open(os.path.join(self.target_dir, MANIFEST_FILENAME), 'r') as f:
            reader = csv.reader(f)
            row = reader.next()
            self.assertEquals(row[0], cloned_unit.unit_key['name'])
            self.assertEquals(row[1], cloned_unit.unit_key['checksum'])
            self.assertEquals(row[2], str(cloned_unit.unit_key['size']))

    @patch('pulp.server.managers.repo._common.get_working_directory', spec_set=True)
    def test_publish_repo_unit_removal(self, mock_get_working, force_full=True):
        mock_get_working.return_value = self.temp_dir
        # Publish a repository
        distributor = self.create_distributor_with_mocked_api_calls()
        config = PluginCallConfiguration({}, {}, {'force_full': force_full})
        distributor.publish_repo(self.repo, self.publish_conduit, config)
        target_file = os.path.join(self.target_dir, SAMPLE_RPM)
        # test if the link was created
        self.assertTrue(os.path.islink(target_file))
        with open(os.path.join(self.target_dir, MANIFEST_FILENAME), 'r') as f:
            self.assertEqual(len(f.readlines()), 1)

        # Remove the unit
        new_conduit = get_publish_conduit(existing_units=[])
        distributor.publish_repo(self.repo, new_conduit, config)
        # Ensure PULP_MANIFEST is updated correctly
        with open(os.path.join(self.target_dir, MANIFEST_FILENAME), 'r') as f:
            self.assertEqual(len(f.readlines()), 0)
        self.assertFalse(os.path.islink(target_file))

    def test_repo_publish_api_calls_fast_forward(self):
        self.test_repo_publish_api_calls(force_full=False)

    def test_repo_publish_files_placed_properly_fast_forward(self):
        self.test_repo_publish_files_placed_properly(force_full=False)

    def test_repo_publish_metadata_writing_fast_forward(self):
        self.test_repo_publish_metadata_writing(force_full=False)

    def test_repo_publish_handles_errors_fast_forward(self):
        self.test_repo_publish_handles_errors(force_full=False)

    def test_republish_after_unit_removal_fast_forward(self):
        self.test_republish_after_unit_removal(force_full=False)

    def test_publish_repo_unit_removal_fast_forward(self):
        self.test_publish_repo_unit_removal(force_full=False)

    @patch('pulp.server.managers.repo._common.get_working_directory', spec_set=True)
    def test_publish_repo_bson_doc_too_large(self, mock_get_working, force_full=False):
        """
        It verifies if too many (>50k+) files will publish with force full to avoid the
        exception[0] "BSON document too large (20946918 bytes) - the connected serversupports
        BSON document sizes up to 16777216 bytes.

        [0] https://pulp.plan.io/issues/5058
        """
        mock_get_working.return_value = self.temp_dir
        distributor = self.create_distributor_with_mocked_api_calls()
        # publish a new repo with  units in it
        units = []
        for i in range(50001):
            cloned_unit = copy.deepcopy(self.unit)
            cloned_unit.unit_key['name'] = "foo%d.rpm" % (i)
            cloned_unit.unit_key['checksum'] = "sum%s" % (1000000000 + i)
            units.append(cloned_unit)
        new_conduit = get_publish_conduit(
            existing_units=units,
            last_published="2019-12-05 19:40:26.284627"
        )
        distributor.publish_repo(self.repo, new_conduit, PluginCallConfiguration({}, {}, {}))
        # Verify if do publish with force full after trying with fast forward
        self.assertEqual(distributor.get_hosting_locations.call_count, 3)

        units = []
        for i in range(5):
            cloned_unit = copy.deepcopy(self.unit)
            cloned_unit.unit_key['name'] = "fooa%d.rpm" % (i)
            cloned_unit.unit_key['checksum'] = "suma%s" % (1000000000 + i)
            units.append(cloned_unit)
        new_conduit = get_publish_conduit(
            existing_units=units,
            last_published="2019-12-05 19:40:26.284627"
        )
        distributor.publish_repo(self.repo, new_conduit, PluginCallConfiguration({}, {}, {}))
        # Verify if do publish with fast forward
        self.assertEqual(distributor.get_hosting_locations.call_count, 4)

    @patch('pulp.server.managers.repo._common.get_working_directory', spec_set=True)
    def test_publish_repo_way_by_conditions(self, mock_get_working):
        """
        Test conditions decides to do publish with fast_forward or force_full
        """
        mock_get_working.return_value = self.temp_dir
        distributor = self.create_distributor_with_mocked_api_calls()
        target2 = os.path.join(self.temp_dir, "target2")
        distributor.get_hosting_locations.return_value.append(target2)
        # Publish a new repo with units with force full finally after trying fast forward
        units = []
        for i in range(4):
            cloned_unit = copy.deepcopy(self.unit)
            cloned_unit.unit_key['name'] = "foo%d.rpm" % (i)
            cloned_unit.unit_key['checksum'] = "sum%s" % (1000000000 + i)
            units.append(cloned_unit)
        new_conduit = get_publish_conduit(
            existing_units=units,
            last_published="2019-12-05 19:40:26.284627"
        )
        distributor.publish_repo(self.repo, new_conduit, PluginCallConfiguration({}, {}, {}))
        # Verify if do publish with force full finally after trying with fast forward
        self.assertEqual(distributor.get_hosting_locations.call_count, 3)

        # Publish the repo with units with fast forward
        for i in range(2):
            cloned_unit = copy.deepcopy(self.unit)
            cloned_unit.unit_key['name'] = "food%d.rpm" % (i)
            cloned_unit.unit_key['checksum'] = "sumd%s" % (1000000000 + i)
            units.append(cloned_unit)
        new_conduit = get_publish_conduit(
            existing_units=units,
            last_published="2019-12-05 19:40:26.284627"
        )
        distributor.publish_repo(self.repo, new_conduit, PluginCallConfiguration({}, {}, {}))
        # Verify if do publish with fast forward
        self.assertEqual(distributor.get_hosting_locations.call_count, 4)

    def test_distributor_removed_calls_unpublish(self):
        distributor = self.create_distributor_with_mocked_api_calls()
        distributor.unpublish_repo = Mock()
        distributor.distributor_removed(self.repo, {})
        self.assertTrue(distributor.unpublish_repo.called)

    @patch('pulp.server.managers.repo._common.get_working_directory', spec_set=True)
    def test_unpublish_repo(self, mock_get_working):
        mock_get_working.return_value = self.temp_dir
        distributor = self.create_distributor_with_mocked_api_calls()
        distributor.publish_repo(self.repo, self.publish_conduit, PluginCallConfiguration({}, {},
                                                                                          {}))
        self.assertTrue(os.path.exists(self.target_dir))
        distributor.unpublish_repo(self.repo, {})
        self.assertFalse(os.path.exists(self.target_dir))

    def test__rmtree_if_exists(self):
        """
        Let's just make sure this simple thing doesn't barf.
        """
        a_directory = os.path.join(self.temp_dir, 'a_directory')
        test_filename = os.path.join(a_directory, 'test.txt')
        os.makedirs(a_directory)
        with open(test_filename, 'w') as test:
            test.write("Please don't barf.")

        # This should not cause any problems, and test.txt should still exist
        distributor = self.create_distributor_with_mocked_api_calls()
        distributor._rmtree_if_exists(os.path.join(self.temp_dir, 'fake_path'))
        self.assertTrue(os.path.exists(test_filename))

        # Now let's remove a_directory
        distributor._rmtree_if_exists(a_directory)
        self.assertFalse(os.path.exists(a_directory))

    @patch('pulp.plugins.file.distributor.FileDistributor._target_symlink_path',
           side_effect=FileDistributor._target_symlink_path)
    def test__symlink_units(self, mock__target_symlink_path):
        """
        Make sure that the _symlink_units creates all the correct symlinks.
        """

        distributor = self.create_distributor_with_mocked_api_calls()

        # There's some logic in _symlink_units to handle preexisting files and symlinks, so let's
        # create some fakes to see if it does the right thing
        build_dir = os.path.join(self.temp_dir, BUILD_DIRNAME)
        os.makedirs(build_dir)
        os.symlink('/some/weird/path',
                   os.path.join(build_dir, self.unit.unit_key['name']))

        distributor._symlink_unit(build_dir, self.unit, [self.unit.unit_key['name'], ])

        expected_symlink_path = os.path.join(build_dir, self.unit.unit_key['name'])
        self.assertTrue(os.path.islink(expected_symlink_path))
        expected_symlink_destination = os.path.join(DATA_DIR, self.unit.unit_key['name'])
        self.assertEqual(os.path.realpath(expected_symlink_path), expected_symlink_destination)
        mock__target_symlink_path.assert_called_once_with(build_dir, self.unit.unit_key['name'])

    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    @patch('os.symlink')
    def test__symlink_unit_with_subdir(self, mock_symlink, mock_makedirs, mock_exists):
        """
        Make sure that if the file being published has to go in a subdirectory, that subdirectory
        gets created.
        """
        distributor = self.create_distributor_with_mocked_api_calls()

        distributor._symlink_unit('/a/b/c/', self.unit, ['d/e/f.txt', ])

        mock_makedirs.assert_called_once_with('/a/b/c/d/e')

    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    @patch('os.symlink')
    def test__symlink_unit_with_existing_subdir(self, mock_symlink, mock_makedirs, mock_exists):
        """
        Make sure that if the file being published has to go in a subdirectory, and that
        subdirectory already exists, no exception is raised.
        """
        e = OSError()
        e.errno = errno.EEXIST
        mock_makedirs.side_effect = e
        distributor = self.create_distributor_with_mocked_api_calls()

        distributor._symlink_unit('/a/b/c/', self.unit, ['d/e/f.txt', ])

        # Make sure the call happened, and otherwise we just care than no exception was raised.
        mock_makedirs.assert_called_once_with('/a/b/c/d/e')

    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    @patch('os.symlink')
    def test__symlink_unit_with_subdir_exception(self, mock_symlink, mock_makedirs, mock_exists):
        """
        Make sure that if the an error other than "already exists" occurs when making the
        sub directory, that exception bubbles up.
        """
        class MyException(Exception):
            pass
        mock_makedirs.side_effect = MyException
        distributor = self.create_distributor_with_mocked_api_calls()

        # make sure this exception was allowed to bubble up
        self.assertRaises(MyException, distributor._symlink_unit,
                          '/a/b/c/', self.unit, ['d/e/f.txt', ])

    @patch('os.symlink', side_effect=os.symlink)
    def test__symlink_units_existing_correct_link(self, symlink):
        """
        Make sure that the _symlink_units handles an existing correct link well.
        """
        # There's some logic in _symlink_units to handle preexisting files and symlinks, so let's
        # create some fakes to see if it does the right thing
        build_dir = os.path.join(self.temp_dir, BUILD_DIRNAME)
        os.makedirs(build_dir)
        expected_symlink_destination = os.path.join(DATA_DIR, self.unit.unit_key['name'])
        os.symlink(expected_symlink_destination,
                   os.path.join(build_dir, self.unit.unit_key['name']))
        # Now let's reset the Mock so that we can make sure it doesn't get called during _symlink
        symlink.reset_mock()

        distributor = self.create_distributor_with_mocked_api_calls()
        distributor._symlink_unit(build_dir, self.unit, [self.unit.unit_key['name']])

        # The call count for symlink should be 0, because the _symlink_units call should have
        # noticed that the symlink was already correct and thus should have skipped it
        self.assertEqual(symlink.call_count, 0)
        expected_symlink_path = os.path.join(build_dir, self.unit.unit_key['name'])
        self.assertTrue(os.path.islink(expected_symlink_path))
        self.assertEqual(os.path.realpath(expected_symlink_path),
                         os.path.realpath(expected_symlink_destination))

    @patch('os.readlink')
    def test__symlink_units_os_error(self, readlink):
        """
        Make sure that the _symlink_units handles an OSError correctly, for the case where it
        doesn't raise EINVAL. We already have a test that raises EINVAL (test__symlink_units places
        an ordinary file there.)
        """
        os_error = OSError()
        # This would be an unexpected error for reading a symlink!
        os_error.errno = errno.ENOSPC
        readlink.side_effect = os_error
        # There's some logic in _symlink_units to handle preexisting files and symlinks, so let's
        # create some fakes to see if it does the right thing
        build_dir = os.path.join(self.temp_dir, BUILD_DIRNAME)
        os.makedirs(build_dir)

        expected_symlink_destination = os.path.join(DATA_DIR, self.unit.unit_key['name'])
        os.symlink(expected_symlink_destination,
                   os.path.join(build_dir, self.unit.unit_key['name']))

        try:
            distributor = self.create_distributor_with_mocked_api_calls()
            distributor._symlink_unit(build_dir, self.unit, [self.unit.unit_key['name']])
            self.fail('An OSError should have been raised, but was not!')
        except OSError, e:
            self.assertEqual(e.errno, errno.ENOSPC)

    @patch('os.readlink')
    def test__symlink_units_EINVAL_os_error(self, mock_readlink):
        """
        Make sure that the _symlink_units handles an OSError correctly, for the case where it
        raises EINVAL. We already have a test that raises EINVAL (test__symlink_units places
        an ordinary file there.)
        """
        os_error = OSError()
        # This would be an unexpected error for reading a symlink!
        os_error.errno = errno.EINVAL
        mock_readlink.side_effect = os_error
        # There's some logic in _symlink_units to handle preexisting files and symlinks, so let's
        # create some fakes to see if it does the right thing
        build_dir = os.path.join(self.temp_dir, BUILD_DIRNAME)
        os.makedirs(build_dir)

        original_link = os.path.join(build_dir, self.unit.unit_key['name'])
        old_target = os.path.join(DATA_DIR, SAMPLE_FILE)
        os.symlink(old_target, original_link)

        distributor = self.create_distributor_with_mocked_api_calls()
        distributor._symlink_unit(build_dir, self.unit, [self.unit.unit_key['name']])

        # make sure the symlink was deleted
        self.assertTrue(os.path.islink(original_link))
        created_link = readlink(original_link)
        self.assertNotEqual(old_target, created_link)

    @patch('os.path.join')
    @patch('os.path.isabs')
    @patch('os.path.normpath')
    def test__target_symlink_path_gears_wheel(self, mock_normpath, mock_isabs, mock_join):
        """
        Check the gears wheel as expected in _target_symlink_path.
        """
        distributor = self.create_distributor_with_mocked_api_calls()
        # not substantial for the test
        build_dir = '/foo/bar'
        target_path = 'baz'
        # set up mock return values according to an OK pass thru the gears
        norm_mock = mock_normpath.return_value
        mock_isabs.return_value = False
        norm_mock.startswith.return_value = False
        norm_mock.__eq__.return_value = False

        ret = distributor._target_symlink_path(build_dir, target_path)

        mock_normpath.assert_called_once_with(target_path)
        mock_isabs.assert_called_once_with(norm_mock)
        norm_mock.startswith.assert_called_once_with('../')
        norm_mock.__eq__.assert_called_once_with('..')
        mock_join.assert_called_once_with(build_dir, norm_mock)
        self.assertIs(mock_join.return_value, ret)

    @patch('os.path.join', side_effect=os.path.join)
    @patch('os.path.isabs', side_effect=os.path.isabs)
    @patch('os.path.normpath', side_effect=os.path.normpath)
    def test__target_symlink_path_with_OK_path(self, mock_normpath, mock_isabs, mock_join):
        """
        Check an OK target path returns an expected target symlink path.
        """
        distributor = self.create_distributor_with_mocked_api_calls()
        build_dir = '/foo/bar'
        target_path = 'foo/.././..baz/.bar'
        expected_normpath = '..baz/.bar'
        expected_symlink_path = '/foo/bar/..baz/.bar'

        self.assertEqual(expected_symlink_path, distributor._target_symlink_path(build_dir,
                                                                                 target_path))
        mock_normpath.assert_called_once_with(target_path)
        mock_isabs.assert_called_once_with(expected_normpath)
        mock_join.assert_called_once_with(build_dir, expected_normpath)

    @patch('os.path.join')
    @patch('os.path.isabs', side_effect=os.path.isabs)
    @patch('os.path.normpath', side_effect=os.path.normpath)
    def test__target_symlink_path_with_absolute_path(self, mock_normpath, mock_isabs, mock_join):
        """
        Check an absolute target path fails the symlink validation.
        """
        distributor = self.create_distributor_with_mocked_api_calls()
        build_dir = '/foo/bar'
        target_path = '/baz'

        self.assertRaisesRegexp(ValueError, '.*absolute: %s' % target_path,
                                distributor._target_symlink_path,
                                build_dir, target_path)
        mock_normpath.assert_called_once_with(target_path)
        mock_isabs.assert_called_once_with(os.path.normpath(target_path))
        mock_join.assert_not_called()

    @patch('os.path.join')
    @patch('os.path.isabs', side_effect=os.path.isabs)
    @patch('os.path.normpath', side_effect=os.path.normpath)
    def test__target_symlink_path_outside_build_dir_as_parent_dir(self, mock_normpath, mock_isabs,
                                                                  mock_join):
        """
        Check the target path `..` fails the symlink validation.
        """
        distributor = self.create_distributor_with_mocked_api_calls()
        build_dir = '/foo/bar'
        target_path = 'baz/../../'

        self.assertRaisesRegexp(ValueError, '.*outside.*%s' % target_path,
                                distributor._target_symlink_path,
                                build_dir, target_path)
        mock_normpath.assert_called_once_with(target_path)
        mock_isabs.assert_called_once_with('..')
        mock_join.assert_not_called()

    @patch('os.path.join')
    @patch('os.path.isabs', side_effect=os.path.isabs)
    @patch('os.path.normpath', side_effect=os.path.normpath)
    def test__target_symlink_path_outside_build_dir(self, mock_normpath, mock_isabs, mock_join):
        """
        Check a target path outside of build dir fails the symlink validation.
        """
        distributor = self.create_distributor_with_mocked_api_calls()
        build_dir = '/foo/bar'
        target_path = 'baz/../../../fizz'

        self.assertRaisesRegexp(ValueError, '.*outside.*%s' % target_path,
                                distributor._target_symlink_path,
                                build_dir, target_path)
        mock_normpath.assert_called_once_with(target_path)
        mock_isabs.assert_called_once_with('../../fizz')
        mock_join.assert_not_called()
