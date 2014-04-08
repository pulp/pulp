import os
import sys
import tempfile
import traceback
import unittest
import mock

from pulp.common.plugins import reporting_constants
from pulp.devel.unit.util import touch, compare_dict
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.model import Repository
from pulp.plugins.conduits.repo_publish import RepoPublishConduit
from pulp.plugins.util.publish_step import PublishStep, UnitPublishStep, BasePublisher


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
        self.publisher = BasePublisher(self.repo, self.conduit, self.config)


class PublishStepTests(PublisherBase):

    def test_get_working_dir(self):
        step = PublishStep('foo_step')
        step.parent = mock.Mock()
        step.parent.working_dir = 'foo'
        working_dir = step.get_working_dir()
        self.assertEquals(working_dir, 'foo')

    def test_get_repo(self):
        step = PublishStep('foo_step')
        step.parent = mock.Mock(repo='foo')
        self.assertEquals('foo', step.get_repo())

    def test_get_conduit(self):
        step = PublishStep('foo_step')
        step.parent = mock.Mock(conduit='foo')
        self.assertEquals('foo', step.get_conduit())

    def test_get_step(self):
        step = PublishStep('foo_step')
        step.parent = mock.Mock()
        other_step = step.get_step('other')
        step.parent.get_step.assert_called_once_with('other')
        self.assertEquals(other_step, step.parent.get_step())

    @mock.patch('pulp.server.async.task_status_manager.TaskStatusManager.update_task_status')
    @mock.patch('pulp.plugins.conduits.repo_publish.RepoPublishConduit.get_units')
    def test_process_step_failure_reported_on_metadata_finalized(self, mock_get_units, mock_update):
        self.publisher.repo.content_unit_counts = {'FOO_TYPE': 1}
        mock_get_units.return_value = ['mock_unit']
        step = PublishStep('foo_step')
        step.parent = self.publisher
        step.finalize_metadata = mock.Mock(side_effect=Exception())
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
        publish_step.parent.report_progress.assert_called_once_with()

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
            reporting_constants.PROGRESS_SUCCESSES_KEY: 1,
            reporting_constants.PROGRESS_STATE_KEY: step.state,
            reporting_constants.PROGRESS_ERROR_DETAILS_KEY: step.error_details,
            reporting_constants.PROGRESS_PROCESSED_KEY: 2,
            reporting_constants.PROGRESS_FAILURES_KEY: 1,
            reporting_constants.PROGRESS_TOTAL_KEY: 2
        }

        compare_dict(report, target_report)

    def test_get_progress_report_summary(self):
        step = PublishStep('foo_step')
        step.state = reporting_constants.STATE_COMPLETE
        report = step.get_progress_report_summary()
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

    @mock.patch('pulp.server.async.task_status_manager.TaskStatusManager.update_task_status')
    def test_process_step_no_units(self, mock_update):
        self.publisher.repo.content_unit_counts = {'FOO_TYPE': 0}
        mock_method = mock.Mock()
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
        self.publisher._add_steps([step], self.publisher.process_steps)
        step.parent = self.publisher

        step.process_unit = self._step_canceler
        step.process()

        self.assertEquals(step.state, reporting_constants.STATE_CANCELLED)
        self.assertEquals(step.progress_successes, 1)
        self.assertEquals(step.progress_failures, 0)
        self.assertEquals(step.total_units, 2)

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


class BasePublisherTests(PublisherBase):

    @mock.patch('pulp.plugins.conduits.repo_publish.RepoPublishConduit.get_units')
    def test_publish(self, mock_get_units):
        mock_get_units.return_value = []
        metadata_step = PublishStep('metadata')
        metadata_step.initialize_metadata = mock.Mock()
        metadata_step.finalize_metadata = mock.Mock()
        process_step = PublishStep('process')
        process_step.process = mock.Mock()
        post_process_step = PublishStep('post_process')
        post_process_step.process = mock.Mock()
        base_publish = BasePublisher(self.publisher.repo,
                                     self.publisher.conduit,
                                     self.publisher.config,
                                     initialize_metadata_steps=[metadata_step],
                                     process_steps=[process_step],
                                     finalize_metadata_steps=[metadata_step],
                                     post_metadata_process_steps=[post_process_step])

        base_publish.publish()
        metadata_step.initialize_metadata.assert_called_once_with()
        metadata_step.finalize_metadata.assert_called_once_with()
        process_step.process.assert_called_once_with()
        post_process_step.process.assert_called_once_with()

    @mock.patch('pulp.plugins.conduits.repo_publish.RepoPublishConduit.get_units')
    def test_publish_initialize_working_dir(self, mock_get_units):
        mock_get_units.return_value = []
        metadata_step = PublishStep('metadata')
        metadata_step.initialize_metadata = mock.Mock()
        metadata_step.finalize_metadata = mock.Mock()
        process_step = PublishStep('process')
        process_step.process = mock.Mock()
        post_process_step = PublishStep('post_process')
        post_process_step.process = mock.Mock()
        base_publish = BasePublisher(self.publisher.repo,
                                     self.publisher.conduit,
                                     self.publisher.config,
                                     initialize_metadata_steps=[metadata_step],
                                     process_steps=[process_step],
                                     finalize_metadata_steps=[metadata_step],
                                     post_metadata_process_steps=[post_process_step])

        base_publish.working_dir = os.path.join(base_publish.working_dir, 'foo')
        base_publish.publish()
        metadata_step.initialize_metadata.assert_called_once_with()
        metadata_step.finalize_metadata.assert_called_once_with()
        process_step.process.assert_called_once_with()
        post_process_step.process.assert_called_once_with()

    def test_publish_with_error(self):
        mock_metadata_step = mock.MagicMock(spec=PublishStep)
        mock_metadata_step.step_id = 'metadata'
        mock_metadata_step.initialize_metadata.side_effect = Exception('foo')
        mock_process_step = mock.MagicMock(spec=PublishStep)
        mock_process_step.step_id = 'process'
        mock_post_process_step = mock.MagicMock(spec=PublishStep)
        mock_post_process_step.step_id = 'post_process'
        base_publish = BasePublisher(self.publisher.repo,
                                     self.publisher.conduit,
                                     self.publisher.config,
                                     initialize_metadata_steps=[mock_metadata_step],
                                     process_steps=[mock_process_step],
                                     finalize_metadata_steps=[mock_metadata_step],
                                     post_metadata_process_steps=[mock_post_process_step])
        self.assertRaises(Exception, base_publish.publish)
        mock_metadata_step.initialize_metadata.assert_called_once_with()

        self.assertTrue(mock_metadata_step.finalize_metadata.called)
        self.assertFalse(mock_process_step.process.called)
        self.assertFalse(mock_post_process_step.process.called)

    def test_two_step_with_same_id_fails(self):
        mock_metadata_step = mock.MagicMock(spec=PublishStep)
        mock_metadata_step.step_id = 'metadata'
        mock_metadata_step_2 = mock.MagicMock(spec=PublishStep)
        mock_metadata_step_2.step_id = 'metadata'
        self.assertRaises(ValueError, BasePublisher, self.publisher.repo,
                          self.publisher.conduit,
                          self.publisher.config,
                          initialize_metadata_steps=[mock_metadata_step, mock_metadata_step_2])

    def test_get_step(self):
        mock_metadata_step = mock.MagicMock(spec=PublishStep)
        mock_metadata_step.step_id = 'metadata'
        mock_process_step = mock.MagicMock(spec=PublishStep)
        mock_process_step.step_id = 'process'
        mock_post_process_step = mock.MagicMock(spec=PublishStep)
        mock_post_process_step.step_id = 'post_process'
        base_publish = BasePublisher(self.publisher.repo,
                                     self.publisher.conduit,
                                     self.publisher.config,
                                     initialize_metadata_steps=[mock_metadata_step],
                                     process_steps=[mock_process_step],
                                     finalize_metadata_steps=[mock_metadata_step],
                                     post_metadata_process_steps=[mock_post_process_step])

        self.assertEquals(mock_metadata_step, base_publish.get_step('metadata'))
        self.assertEquals(mock_process_step, base_publish.get_step('process'))
        self.assertEquals(mock_post_process_step, base_publish.get_step('post_process'))

    def test_build_final_report_success(self):

        step_one = PublishStep('step_one')
        step_one.state = reporting_constants.STATE_COMPLETE
        step_two = PublishStep('step_two')
        step_two.state = reporting_constants.STATE_COMPLETE
        self.publisher._add_steps([step_one, step_two], self.publisher.process_steps)

        report = self.publisher._build_final_report()

        self.assertTrue(report.success_flag)

    def test_build_final_report_failure(self):

        step_one = PublishStep('step_one')
        step_one.state = reporting_constants.STATE_COMPLETE
        step_two = PublishStep('step_two')
        step_two.state = reporting_constants.STATE_FAILED
        self.publisher._add_steps([step_one, step_two], self.publisher.process_steps)

        report = self.publisher._build_final_report()

        self.assertFalse(report.success_flag)

    def test_skip_list_with_list(self):
        mock_config = mock.Mock()
        mock_config.get.return_value = ['foo', 'bar']
        publisher = BasePublisher(self.publisher.repo, self.publisher.conduit, mock_config)

        skip_list = publisher.skip_list
        self.assertEquals(2, len(skip_list))
        self.assertEquals(skip_list[0], 'foo')
        self.assertEquals(skip_list[1], 'bar')

    def test_skip_list_with_dict(self):
        mock_config = mock.Mock()
        mock_config.get.return_value = {'rpm': True, 'distro': False, 'errata': True}
        self.publisher.config = mock_config
        skip_list = self.publisher.skip_list
        self.assertEquals(2, len(skip_list))
        self.assertEquals(skip_list[0], 'rpm')
        self.assertEquals(skip_list[1], 'errata')

    def test_cancel(self):
        mock_step = mock.Mock(step_id='foo')
        self.publisher._add_steps([mock_step], self.publisher.process_steps)
        self.publisher.cancel()

        self.assertTrue(self.publisher.canceled)
        mock_step.cancel.assert_called_once_with()

    def test_cancel_twice(self):
        mock_step = mock.Mock(step_id='foo')
        self.publisher._add_steps([mock_step], self.publisher.process_steps)
        self.publisher.cancel()

        self.assertTrue(self.publisher.canceled)
        mock_step.cancel.assert_called_once_with()

        #reset the step cancel
        mock_step.cancel.reset_mock()

        self.publisher.cancel()
        self.assertEquals(0, mock_step.cancel.call_count)

