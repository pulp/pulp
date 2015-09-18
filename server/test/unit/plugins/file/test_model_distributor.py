import errno
import os
import shutil
import tempfile
import unittest

from mock import Mock, MagicMock, patch

from pulp.devel.mock_distributor import get_publish_conduit
from pulp.plugins.file.distributor import FilePublishProgressReport
from pulp.plugins.file.model_distributor import FileDistributor, BUILD_DIRNAME
from pulp.plugins.model import Repository as OldRepoModel
from pulp.server.db.model import Repository


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
        self.repo.repo_id = "foo"
        self.repo.working_dir = self.temp_dir
        self.old_repo_model = MagicMock(spec=OldRepoModel)
        self.old_repo_model.repo_obj = self.repo
        self.old_repo_model.id = "foo"
        self.unit = MagicMock(unit_type_id='RPM', name=SAMPLE_RPM, size=1, checksum='sum1',
                              unit_key={'name': SAMPLE_RPM, 'checksum': 'sum1', 'size': 1})
        self.unit.storage_path = os.path.join(__file__, DATA_DIR, SAMPLE_RPM)
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

    def test_post_repo_publish_not_broken(self):
        distributor = FileDistributor()
        # ensure that this doesn't raise an error
        distributor.post_repo_publish(None, None)

    @patch('pulp.plugins.file.model_distributor.FileDistributor._symlink_unit')
    @patch('pulp.server.controllers.repository.find_repo_content_units', spec_set=True)
    @patch('pulp.server.managers.repo._common.get_working_directory', spec_set=True)
    def test_repo_publish_api_calls(self, mock_get_working_dir, mock_find, mock_symlink):
        mock_get_working_dir.return_value = self.temp_dir
        mock_find.return_value = [self.unit]

        distributor = self.create_distributor_with_mocked_api_calls()
        result = distributor.publish_repo(self.old_repo_model, self.publish_conduit, {})
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

    def test_repo_publish_metadata_writing(self):
        distributor = self.create_distributor_with_mocked_api_calls()
        distributor.metadata_csv_writer = MagicMock()

        distributor.publish_metadata_for_unit(self.unit)

        writerow = distributor.metadata_csv_writer.writerow
        writerow.assert_called_once_with([self.unit.unit_key['name'],
                                         self.unit.unit_key['checksum'],
                                         self.unit.unit_key['size']])

    @patch('pulp.server.managers.repo._common.get_working_directory', spec_set=True)
    @patch('pulp.plugins.file.model_distributor._logger')
    def test_repo_publish_handles_errors(self, mock_logger, mock_get_working_dir):
        """
        Make sure that publish() does the right thing with the report when there is an error.
        """
        mock_get_working_dir.return_value = self.temp_dir
        distributor = self.create_distributor_with_mocked_api_calls()
        distributor.post_repo_publish.side_effect = Exception('Rawr!')

        report = distributor.publish_repo(self.old_repo_model, self.publish_conduit, {})

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

    def test_distributor_removed_calls_unpublish(self):
        distributor = self.create_distributor_with_mocked_api_calls()
        distributor.unpublish_repo = Mock()
        distributor.distributor_removed(self.repo, {})
        self.assertTrue(distributor.unpublish_repo.called)

    @patch('pulp.plugins.file.model_distributor.FileDistributor._rmtree_if_exists', spec_set=True)
    def test_unpublish_repo(self, mock_rmtree):
        distributor = self.create_distributor_with_mocked_api_calls()

        distributor.unpublish_repo(self.old_repo_model, {})

        mock_rmtree.assert_called_once_with(self.target_dir)

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

    def test__symlink_units(self):
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
    def test__symlink_units_os_error(self, mock_readlink):
        """
        Make sure that the _symlink_units handles an OSError correctly, for the case where it
        doesn't raise EINVAL. We already have a test that raises EINVAL (test__symlink_units places
        an ordinary file there.)
        """
        os_error = OSError()
        # This would be an unexpected error for reading a symlink!
        os_error.errno = errno.ENOSPC
        mock_readlink.side_effect = os_error
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

    def test__symlink_units_EINVAL_os_error(self):
        """
        Make sure that the _symlink_units handles an OSError correctly, for the case where it
        raises EINVAL. We already have a test that raises EINVAL (test__symlink_units places
        an ordinary file there.)
        """
        os_error = OSError()
        # This would be an unexpected error for reading a symlink!
        os_error.errno = errno.EINVAL
        with patch('os.readlink') as mock_readlink:
            mock_readlink.side_effect = os_error
            # There's some logic in _symlink_units to handle preexisting files and symlinks,
            # so let's create some fakes to see if it does the right thing
            build_dir = os.path.join(self.temp_dir, BUILD_DIRNAME)
            os.makedirs(build_dir)

            original_link = os.path.join(build_dir, self.unit.unit_key['name'])
            old_target = os.path.join(DATA_DIR, SAMPLE_FILE)
            os.symlink(old_target, original_link)

            distributor = self.create_distributor_with_mocked_api_calls()
            distributor._symlink_unit(build_dir, self.unit, [self.unit.unit_key['name']])

        # make sure the symlink was deleted
        self.assertTrue(os.path.islink(original_link))
        created_link = os.readlink(original_link)
        self.assertNotEqual(old_target, created_link)
