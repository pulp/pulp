import contextlib
import os
import shutil
import sys
import tarfile
import tempfile
import time
import traceback
import unittest

import mock
from mock import Mock, patch

from pulp.common.plugins import reporting_constants
from pulp.devel.unit.util import touch, compare_dict
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.conduits.repo_publish import RepoPublishConduit
from pulp.plugins.model import Repository
from pulp.plugins.util.publish_step import PublishStep, UnitPublishStep, \
    AtomicDirectoryPublishStep, SaveTarFilePublishStep, _post_order, CopyDirectoryStep


class PublisherBase(unittest.TestCase):

    def setUp(self):
        self.working_dir = tempfile.mkdtemp(prefix='working_')
        self.published_dir = tempfile.mkdtemp(prefix='published_')
        self.master_dir = os.path.join(self.published_dir, 'master')

        self.repo_id = 'publish-test-repo'
        self.repo = Repository(self.repo_id, working_dir=self.working_dir)
        self.conduit = mock.Mock()
        self.conduit = RepoPublishConduit(self.repo_id, 'test_distributor_id')
        self.conduit.get_repo_scratchpad = mock.Mock(return_value={})

        self.config = PluginCallConfiguration(None, None)
        self.publisher = PublishStep("base-step", self.repo, self.conduit, self.config,
                                     'test_distributor_type')


class PostOrderTests(unittest.TestCase):

    def test_ordered_output(self):
        class Node:
            def __init__(self, value):
                self.value = value
                self.children = []

        n1 = Node(1)
        n2 = Node(2)
        n3 = Node(3)
        n4 = Node(4)
        n5 = Node(5)

        n5.children = [n1, n4]
        n4.children = [n2, n3]

        value_list = [n.value for n in _post_order(n5)]
        self.assertEquals(value_list, [1, 2, 3, 4, 5])


class PublishStepTests(PublisherBase):

    def test_get_working_dir_already_calculated(self):
        step = PublishStep('foo_step')
        step.working_dir = 'foo'
        self.assertEquals('foo', step.get_working_dir())

    def test_get_working_dir_from_repo(self):
        step = PublishStep('foo_step')
        step.get_repo = Mock(return_value=Mock(working_dir='foo'))
        self.assertEquals('foo', step.get_working_dir())

    def test_get_repo(self):
        step = PublishStep('foo_step')
        step.repo = 'foo'
        self.assertEquals('foo', step.get_repo())

    def test_get_repo_from_parent(self):
        step = PublishStep('foo_step')
        step.publish_conduit = 'foo'
        step.parent = mock.Mock()
        step.parent.get_repo.return_value = 'foo'
        self.assertEquals('foo', step.get_repo())

    def test_get_distributor_type(self):
        step = PublishStep('foo_step')
        step.distributor_type = 'foo'
        self.assertEquals('foo', step.get_distributor_type())

    def test_get_distributor_type_none(self):
        step = PublishStep('foo_step')
        self.assertEquals(None, step.get_distributor_type())

    def test_get_distributor_type_from_parent(self):
        step = PublishStep('foo_step')
        step.publish_conduit = 'foo'
        step.parent = mock.Mock()
        step.parent.get_distributor_type.return_value = 'foo'
        self.assertEquals('foo', step.get_distributor_type())

    def test_get_conduit(self):
        step = PublishStep('foo_step')
        step.publish_conduit = 'foo'
        self.assertEquals('foo', step.get_conduit())

    def test_get_conduit_from_parent(self):
        step = PublishStep('foo_step')
        step.publish_conduit = 'foo'
        step.parent = mock.Mock()
        step.parent.get_conduit.return_value = 'foo'
        self.assertEquals('foo', step.get_conduit())

    @mock.patch('pulp.server.async.task_status_manager.TaskStatusManager.update_task_status')
    @mock.patch('pulp.plugins.conduits.repo_publish.RepoPublishConduit.get_units')
    def test_process_step_failure_reported_on_metadata_finalized(self, mock_get_units, mock_update):
        self.publisher.repo.content_unit_counts = {'FOO_TYPE': 1}
        mock_get_units.return_value = ['mock_unit']
        step = PublishStep('foo_step')
        step.parent = self.publisher
        step.finalize = mock.Mock(side_effect=Exception())
        self.assertRaises(Exception, step.process)
        self.assertEquals(step.state, reporting_constants.STATE_FAILED)
        self.assertEquals(step.progress_successes, 1)
        self.assertEquals(step.progress_failures, 1)
        self.assertEquals(step.total_units, 1)

    def test_cancel_before_processing(self):
        self.publisher.repo.content_unit_counts = {'FOO_TYPE': 2}
        step = PublishStep('foo_step')
        step.is_skipped = mock.Mock()
        step.cancel()
        step.process()
        self.assertEquals(0, step.is_skipped.call_count)

    def test_report_progress(self):
        publish_step = PublishStep('foo_step')
        publish_step.parent = mock.Mock()
        publish_step.report_progress()
        publish_step.parent.report_progress.assert_called_once_with(False)

    def test_record_failure(self):
        publish_step = PublishStep('foo_step')
        publish_step.parent = self.publisher

        error_msg = 'Too bad, so sad'

        try:
            raise Exception(error_msg)

        except Exception, e:
            tb = sys.exc_info()[2]
            publish_step._record_failure(e, tb)

        self.assertEquals(publish_step.progress_failures, 1)
        details = {'error': e.message,
                   'traceback': '\n'.join(traceback.format_tb(tb))}
        self.assertEqual(publish_step.error_details[0], details)

    def test_get_progress_report(self):
        step = PublishStep('foo_step')
        step.error_details = "foo"
        step.state = reporting_constants.STATE_COMPLETE
        step.total_units = 2
        step.progress_successes = 1
        step.progress_failures = 1
        report = step.get_progress_report()

        target_report = {
            reporting_constants.PROGRESS_STEP_TYPE_KEY: 'foo_step',
            reporting_constants.PROGRESS_NUM_SUCCESSES_KEY: 1,
            reporting_constants.PROGRESS_STATE_KEY: step.state,
            reporting_constants.PROGRESS_ERROR_DETAILS_KEY: step.error_details,
            reporting_constants.PROGRESS_NUM_PROCESSED_KEY: 2,
            reporting_constants.PROGRESS_NUM_FAILURES_KEY: 1,
            reporting_constants.PROGRESS_ITEMS_TOTAL_KEY: 2,
            reporting_constants.PROGRESS_DESCRIPTION_KEY: '',
            reporting_constants.PROGRESS_STEP_UUID: step.uuid
        }

        compare_dict(report, target_report)

    def test_get_progress_report_description(self):
        step = PublishStep('bar_step')
        step.description = 'bar'
        step.error_details = "foo"
        step.state = reporting_constants.STATE_COMPLETE
        step.total_units = 2
        step.progress_successes = 1
        step.progress_failures = 1
        report = step.get_progress_report()

        target_report = {
            reporting_constants.PROGRESS_STEP_TYPE_KEY: 'bar_step',
            reporting_constants.PROGRESS_NUM_SUCCESSES_KEY: 1,
            reporting_constants.PROGRESS_STATE_KEY: step.state,
            reporting_constants.PROGRESS_ERROR_DETAILS_KEY: step.error_details,
            reporting_constants.PROGRESS_NUM_PROCESSED_KEY: 2,
            reporting_constants.PROGRESS_NUM_FAILURES_KEY: 1,
            reporting_constants.PROGRESS_ITEMS_TOTAL_KEY: 2,
            reporting_constants.PROGRESS_DESCRIPTION_KEY: 'bar',
            reporting_constants.PROGRESS_STEP_UUID: step.uuid
        }

        compare_dict(report, target_report)

    def test_get_progress_report_summary(self):
        parent_step = PublishStep('parent_step')
        step = PublishStep('foo_step')
        parent_step.add_child(step)
        step.state = reporting_constants.STATE_COMPLETE
        report = parent_step.get_progress_report_summary()
        target_report = {
            'foo_step': reporting_constants.STATE_COMPLETE
        }
        compare_dict(report, target_report)

    def test_create_symlink(self):
        source_path = os.path.join(self.working_dir, 'source')
        link_path = os.path.join(self.published_dir, 'link')

        touch(source_path)
        self.assertFalse(os.path.exists(link_path))

        PublishStep._create_symlink(source_path, link_path)

        self.assertTrue(os.path.exists(link_path))
        self.assertTrue(os.path.islink(link_path))
        self.assertEqual(os.readlink(link_path), source_path)

    def test_create_symlink_no_source(self):
        source_path = os.path.join(self.working_dir, 'source')
        link_path = os.path.join(self.published_dir, 'link')

        self.assertRaises(RuntimeError, PublishStep._create_symlink, source_path, link_path)

    def test_create_symlink_no_link_parent(self):
        source_path = os.path.join(self.working_dir, 'source')
        link_path = os.path.join(self.published_dir, 'foo/bar/baz/link')

        touch(source_path)
        self.assertFalse(os.path.exists(os.path.dirname(link_path)))

        PublishStep._create_symlink(source_path, link_path)

        self.assertTrue(os.path.exists(link_path))

    def test_create_symlink_link_parent_bad_permissions(self):
        source_path = os.path.join(self.working_dir, 'source')
        link_path = os.path.join(self.published_dir, 'foo/bar/baz/link')

        touch(source_path)
        os.makedirs(os.path.dirname(link_path))
        os.chmod(os.path.dirname(link_path), 0000)

        self.assertRaises(OSError, PublishStep._create_symlink, source_path, link_path)

        os.chmod(os.path.dirname(link_path), 0777)

    def test_create_symlink_link_exists(self):
        old_source_path = os.path.join(self.working_dir, 'old_source')
        new_source_path = os.path.join(self.working_dir, 'new_source')
        link_path = os.path.join(self.published_dir, 'link')

        touch(old_source_path)
        touch(new_source_path)

        os.symlink(old_source_path, link_path)

        self.assertEqual(os.readlink(link_path), old_source_path)

        link_path_with_slash = link_path + '/'

        PublishStep._create_symlink(new_source_path, link_path_with_slash)

        self.assertEqual(os.readlink(link_path), new_source_path)

    def test_create_symlink_link_exists_and_is_correct(self):
        new_source_path = os.path.join(self.working_dir, 'new_source')
        link_path = os.path.join(self.published_dir, 'link')

        touch(new_source_path)

        os.symlink(new_source_path, link_path)

        self.assertEqual(os.readlink(link_path), new_source_path)

        PublishStep._create_symlink(new_source_path, link_path)

        self.assertEqual(os.readlink(link_path), new_source_path)

    def test_create_symlink_link_exists_not_link(self):
        source_path = os.path.join(self.working_dir, 'source')
        link_path = os.path.join(self.published_dir, 'link')

        touch(source_path)
        touch(link_path)

        self.assertRaises(RuntimeError, PublishStep._create_symlink, source_path, link_path)

    def test_clear_directory(self):

        for file_name in ('one', 'two', 'three'):
            touch(os.path.join(self.working_dir, file_name))

        os.makedirs(os.path.join(self.working_dir, 'four'))
        self.assertEqual(len(os.listdir(self.working_dir)), 4)
        step = PublishStep("foo")

        step._clear_directory(self.working_dir, ['two'])

        self.assertEqual(len(os.listdir(self.working_dir)), 1)

    def test_clear_directory_that_does_not_exist(self):
        # If this doesn't throw we are ok
        step = PublishStep("foo")
        step._clear_directory(os.path.join(self.working_dir, 'imaginary'))

    def test_get_total(self):
        step = PublishStep("foo")
        self.assertEquals(1, step._get_total())

    def test_clear_children(self):
        step = PublishStep("foo")
        step.children = ['bar']
        step.clear_children()
        self.assertEquals(0, len(step.children))

    @patch('pulp.plugins.util.publish_step.shutil.rmtree')
    def test_publish(self, mock_rmtree):
        step = PublishStep("foo")
        work_dir = os.path.join(self.working_dir, 'foo')
        step.working_dir = work_dir
        step.process_lifecycle = Mock()
        step._build_final_report = Mock()

        step.publish()
        self.assertTrue(step.process_lifecycle.called)
        self.assertTrue(step._build_final_report.called)
        mock_rmtree.assert_called_once_with(work_dir, ignore_errors=True)

    @patch('pulp.plugins.util.publish_step.shutil.rmtree')
    def test_publish_exception_still_removes_working_dir(self, mock_rmtree):
        step = PublishStep("foo")
        work_dir = os.path.join(self.working_dir, 'foo')
        step.working_dir = work_dir
        step.process_lifecycle = Mock(side_effect=Exception('foo'))
        step._build_final_report = Mock()

        self.assertRaises(Exception, step.publish)
        self.assertTrue(step.process_lifecycle.called)
        self.assertFalse(step._build_final_report.called)
        mock_rmtree.assert_called_once_with(work_dir, ignore_errors=True)

    def test_process_lifecycle(self):
        step = PublishStep('parent')
        step.process = Mock()
        child_step = PublishStep('child')
        child_step.process = Mock()
        step.add_child(child_step)
        step.report_progress = Mock()

        step.process_lifecycle()

        step.process.assert_called_once_with()
        child_step.process.assert_called_once_with()
        step.report_progress.assert_called_once_with(force=True)

    def test_process_lifecycle_reports_on_error(self):
        step = PublishStep('parent')
        step.process = Mock(side_effect=Exception('Foo'))
        step.report_progress = Mock()

        self.assertRaises(Exception, step.process_lifecycle)

        step.report_progress.assert_called_once_with(force=True)

    def test_process_child_on_error_notifies_parent(self):
        step = PublishStep('parent')
        child_step = PublishStep('child')
        child_step.initialize = Mock(side_effect=Exception('boo'))
        child_step.on_error = Mock(side_effect=Exception('flux'))
        step.on_error = Mock()

        step.add_child(child_step)

        self.assertRaises(Exception, step.process_lifecycle)

        self.assertEquals(reporting_constants.STATE_FAILED, step.state)
        self.assertEquals(reporting_constants.STATE_FAILED, child_step.state)
        self.assertTrue(step.on_error.called)
        self.assertTrue(child_step.on_error.called)

    def test_build_final_report_success(self):

        step_one = PublishStep('step_one')
        step_one.state = reporting_constants.STATE_COMPLETE
        step_two = PublishStep('step_two')
        step_two.state = reporting_constants.STATE_COMPLETE
        self.publisher.add_child(step_one)
        self.publisher.add_child(step_two)

        report = self.publisher._build_final_report()

        self.assertTrue(report.success_flag)

    def test_build_final_report_failure(self):

        self.publisher.state = reporting_constants.STATE_FAILED
        step_one = PublishStep('step_one')
        step_one.state = reporting_constants.STATE_COMPLETE
        step_two = PublishStep('step_two')
        step_two.state = reporting_constants.STATE_FAILED
        self.publisher.add_child(step_one)
        self.publisher.add_child(step_two)

        report = self.publisher._build_final_report()

        self.assertFalse(report.success_flag)


class UnitPublishStepTests(PublisherBase):

    def _step_canceler(self, unit):
        if unit is 'cancel':
            self.publisher.cancel()


    @mock.patch('pulp.server.async.task_status_manager.TaskStatusManager.update_task_status')
    def test_process_step_skip_units(self, mock_update):
        self.publisher.config = PluginCallConfiguration(None, {'skip': ['FOO']})
        step = UnitPublishStep('foo_step', 'FOO')
        step.parent = self.publisher
        step.process()
        self.assertEquals(step.state, reporting_constants.STATE_SKIPPED)

    @mock.patch('pulp.plugins.conduits.repo_publish.RepoPublishConduit.get_units')
    @mock.patch('pulp.server.async.task_status_manager.TaskStatusManager.update_task_status')
    def test_process_step_no_units(self, mock_update, mock_get_units):
        self.publisher.repo.content_unit_counts = {'FOO_TYPE': 0}
        mock_method = mock.Mock()
        mock_get_units.return_value = []
        step = UnitPublishStep('foo_step', 'FOO_TYPE')
        step.parent = self.publisher
        step.process_unit = mock_method
        step.process()
        self.assertEquals(step.state, reporting_constants.STATE_COMPLETE)
        self.assertFalse(mock_method.called)

    @mock.patch('pulp.server.async.task_status_manager.TaskStatusManager.update_task_status')
    @mock.patch('pulp.plugins.conduits.repo_publish.RepoPublishConduit.get_units')
    def test_process_step_single_unit(self, mock_get_units, mock_update):
        self.publisher.repo.content_unit_counts = {'FOO_TYPE': 1}
        mock_method = mock.Mock()
        mock_get_units.return_value = ['mock_unit']
        step = UnitPublishStep('foo_step', 'FOO_TYPE')
        step.parent = self.publisher
        step.process_unit = mock_method
        step.process()

        self.assertEquals(step.state, reporting_constants.STATE_COMPLETE)
        self.assertEquals(step.progress_successes, 1)
        self.assertEquals(step.progress_failures, 0)
        self.assertEquals(step.total_units, 1)
        mock_method.assert_called_once_with('mock_unit')

    @mock.patch('pulp.server.async.task_status_manager.TaskStatusManager.update_task_status')
    @mock.patch('pulp.plugins.conduits.repo_publish.RepoPublishConduit.get_units')
    def test_process_step_single_unit_exception(self, mock_get_units, mock_update):
        self.publisher.repo.content_unit_counts = {'FOO_TYPE': 1}
        mock_method = mock.Mock(side_effect=Exception())
        mock_get_units.return_value = ['mock_unit']
        step = UnitPublishStep('foo_step', 'FOO_TYPE')
        step.parent = self.publisher
        step.process_unit = mock_method

        self.assertRaises(Exception, step.process)
        self.assertEquals(step.state, reporting_constants.STATE_FAILED)
        self.assertEquals(step.progress_successes, 0)
        self.assertEquals(step.progress_failures, 1)
        self.assertEquals(step.total_units, 1)
        mock_method.assert_called_once_with('mock_unit')

    @mock.patch('pulp.server.async.task_status_manager.TaskStatusManager.update_task_status')
    @mock.patch('pulp.plugins.conduits.repo_publish.RepoPublishConduit.get_units')
    def test_process_step_cancelled_mid_unit_processing(self, mock_get_units, mock_update):
        self.publisher.repo.content_unit_counts = {'FOO_TYPE': 2}
        mock_get_units.return_value = ['cancel', 'bar_unit']
        step = UnitPublishStep('foo_step', 'FOO_TYPE')
        self.publisher.add_child(step)

        step.process_unit = self._step_canceler
        step.process()

        self.assertEquals(step.state, reporting_constants.STATE_CANCELLED)
        self.assertEquals(step.progress_successes, 1)
        self.assertEquals(step.progress_failures, 0)
        self.assertEquals(step.total_units, 2)

    def test_is_skipped_list(self):
        step = UnitPublishStep("foo", 'bar')
        step.config = PluginCallConfiguration(None, {'skip': ['bar', 'baz']})
        self.assertTrue(step.is_skipped())

    def test_is_skipped_dict(self):
        step = UnitPublishStep("foo", 'bar')
        step.config = PluginCallConfiguration(None, {'skip': {'bar': True, 'baz': True}})
        self.assertTrue(step.is_skipped())

    def test_is_skipped_list_not_skipped(self):
        step = UnitPublishStep("foo", 'bar')
        step.config = PluginCallConfiguration(None, None)
        self.assertFalse(step.is_skipped())

    def test_is_skipped_dict_not_skipped(self):
        step = UnitPublishStep("foo", 'bar')
        step.config = PluginCallConfiguration(None, None)
        self.assertFalse(step.is_skipped())

    def test_get_total(self):
        step = UnitPublishStep("foo", ['bar', 'baz'])
        step.parent = mock.Mock()
        step.parent.repo.content_unit_counts.get.return_value = 1
        total = step._get_total()
        self.assertEquals(2, total)

    def test_get_total_for_list(self):
        step = UnitPublishStep("foo", ['bar', 'baz'])
        step.parent = mock.Mock()
        step.parent.repo.content_unit_counts.get.return_value = 1
        total = step._get_total()
        self.assertEquals(2, total)

    def test_get_with_association_filter(self):
        step = UnitPublishStep("foo", ['bar', 'baz'])
        step.association_filters = {'foo': 'bar'}
        total = step._get_total()
        self.assertEquals(1, total)

    def test_get_total_for_none(self):
        step = UnitPublishStep("foo", ['bar', 'baz'])
        step.parent = mock.Mock()
        step.parent.repo.content_unit_counts.get.return_value = 0
        total = step._get_total()
        self.assertEquals(0, total)


    def test_process_unit_with_no_work(self):
        # Run the blank process unit to ensure no exceptions are raised
        step = UnitPublishStep("foo", ['bar', 'baz'])
        step.process_unit('foo')


class TestAtomicDirectoryPublishStep(unittest.TestCase):

    def setUp(self):
        self.working_directory = tempfile.mkdtemp()
        self.repo = Mock()

    def tearDown(self):
        shutil.rmtree(self.working_directory)

    def test_process_main_alternate_id(self):
        step = AtomicDirectoryPublishStep('foo', 'bar', 'baz', step_type='alternate')
        self.assertEquals(step.step_id, 'alternate')

    def test_process_main_default_id(self):
        step = AtomicDirectoryPublishStep('foo', 'bar', 'baz')
        self.assertEquals(step.step_id, reporting_constants.PUBLISH_STEP_DIRECTORY)

    def test_process_main(self):
        source_dir = os.path.join(self.working_directory, 'source')
        master_dir = os.path.join(self.working_directory, 'master')
        publish_dir = os.path.join(self.working_directory, 'publish', 'bar')
        publish_dir += '/'
        step = AtomicDirectoryPublishStep(source_dir,
                                                        [('/', publish_dir)], master_dir)
        step.parent = Mock(timestamp=str(time.time()))

        # create some files to test
        sub_file = os.path.join(source_dir, 'foo', 'bar.html')
        touch(sub_file)

        # Create an old directory to test
        old_dir = os.path.join(master_dir, 'foo')
        os.makedirs(old_dir)
        step.process_main()

        target_file = os.path.join(publish_dir, 'foo', 'bar.html')
        self.assertEquals(True, os.path.exists(target_file))
        self.assertEquals(1, len(os.listdir(master_dir)))

    def test_process_main_multiple_targets(self):
        source_dir = os.path.join(self.working_directory, 'source')
        master_dir = os.path.join(self.working_directory, 'master')
        publish_dir = os.path.join(self.working_directory, 'publish', 'bar')
        publish_dir += '/'
        # create some files to test
        sub_file = os.path.join(source_dir, 'foo', 'bar.html')
        touch(sub_file)
        sub_file = os.path.join(source_dir, 'qux', 'quux.html')
        touch(sub_file)

        target_qux = os.path.join(self.working_directory, 'publish', 'qux.html')

        step = AtomicDirectoryPublishStep(source_dir,
                                                        [('/', publish_dir),
                                                         ('qux/quux.html', target_qux)
                                                         ], master_dir)
        step.parent = Mock(timestamp=str(time.time()))

        step.process_main()

        target_file = os.path.join(publish_dir, 'foo', 'bar.html')
        self.assertEquals(True, os.path.exists(target_file))
        self.assertEquals(True, os.path.exists(target_qux))

    def test_process_main_only_publish_directory_contents(self):
        source_dir = os.path.join(self.working_directory, 'source')
        master_dir = os.path.join(self.working_directory, 'master')
        publish_dir = os.path.join(self.working_directory, 'publish', 'bar')
        publish_dir += '/'
        step = AtomicDirectoryPublishStep(source_dir, [('/', publish_dir)], master_dir,
                                          only_publish_directory_contents=True)
        step.parent = Mock(timestamp=str(time.time()))

        # create some files to test
        sub_file = os.path.join(source_dir, 'bar.html')
        touch(sub_file)

        # create an existing file that will be maintained
        existing_file = os.path.join(source_dir, 'bar.html')
        touch(existing_file)

        # Create an old directory to test
        old_dir = os.path.join(master_dir, 'foo')
        os.makedirs(old_dir)
        step.process_main()

        target_file = os.path.join(publish_dir, 'bar.html')
        self.assertEquals(True, os.path.exists(target_file))
        self.assertTrue(os.path.exists(existing_file))
        self.assertEquals(1, len(os.listdir(master_dir)))


class TestSaveTarFilePublishStep(unittest.TestCase):
    def setUp(self):
        self.working_directory = tempfile.mkdtemp()
        self.repo = Mock()

    def tearDown(self):
        shutil.rmtree(self.working_directory)

    def test_process_main(self):
        source_dir = os.path.join(self.working_directory, 'source')
        os.makedirs(source_dir)
        target_file = os.path.join(self.working_directory, 'target', 'target.tar')
        step = SaveTarFilePublishStep(source_dir, target_file)

        touch(os.path.join(source_dir, 'foo.txt'))
        step.process_main()

        with contextlib.closing(tarfile.open(target_file)) as tar_file:
            names = tar_file.getnames()
            self.assertEquals(names, ['', 'foo.txt'])


class TestCopyDirectoryStep(unittest.TestCase):
    def setUp(self):
        self.working_directory = tempfile.mkdtemp()
        self.repo = Mock()

    def tearDown(self):
        shutil.rmtree(self.working_directory)

    def test_process_main(self):
        source_dir = os.path.join(self.working_directory, 'source')
        os.makedirs(source_dir)
        touch(os.path.join(source_dir, 'foo.txt'))
        target_dir = os.path.join(self.working_directory, 'target')

        target_file = os.path.join(target_dir, 'foo.txt')

        step = CopyDirectoryStep(source_dir, target_dir)

        touch(os.path.join(source_dir, 'foo.txt'))
        step.process_main()

        self.assertTrue(os.path.exists(target_file))
