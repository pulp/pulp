import contextlib
import os
import shutil
import sys
import tarfile
import tempfile
import time
import traceback
import unittest

import mongoengine
from mock import Mock, patch, MagicMock
from nectar.downloaders.local import LocalFileDownloader
from nectar.request import DownloadRequest

from pulp.common.plugins import reporting_constants, importer_constants
from pulp.devel.unit.util import touch, compare_dict
from pulp.plugins.conduits.repo_publish import RepoPublishConduit
from pulp.plugins.conduits.repo_sync import RepoSyncConduit
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.model import Repository, SyncReport, Unit
from pulp.plugins.util import publish_step
from pulp.server.db import model
from pulp.server.managers import factory

factory.initialize()


class PublisherBase(unittest.TestCase):

    def setUp(self):
        self.working_dir = tempfile.mkdtemp(prefix='working_')
        self.published_dir = tempfile.mkdtemp(prefix='published_')
        self.master_dir = os.path.join(self.published_dir, 'master')

        self.repo_id = 'publish-test-repo'
        self.repo = Repository(self.repo_id, working_dir=self.working_dir)
        self.conduit = Mock()
        self.conduit = RepoPublishConduit(self.repo_id, 'test_distributor_id')
        self.conduit.get_repo_scratchpad = Mock(return_value={})

        self.config = PluginCallConfiguration(None, None)
        self.publisher = publish_step.PublishStep(
            "base-step", repo=self.repo, publish_conduit=self.conduit,
            config=self.config, distributor_type='test_distributor_type')

    def tearDown(self):
        shutil.rmtree(self.working_dir)
        shutil.rmtree(self.published_dir)


class PluginBase(unittest.TestCase):

    def setUp(self):
        self.working_dir = tempfile.mkdtemp(prefix='working_')

        self.repo_id = 'publish-test-repo'
        self.repo = Repository(self.repo_id, working_dir=self.working_dir)
        self.conduit = RepoPublishConduit(self.repo_id, 'test_plugin_id')
        self.conduit.get_repo_scratchpad = Mock(return_value={})

        self.config = PluginCallConfiguration(None, None)
        self.pluginstep = publish_step.PluginStep(
            "base-step", repo=self.repo, conduit=self.conduit,
            config=self.config, plugin_type='test_plugin_type')


class TestUnitModelPluginStep(PluginBase):
    def setUp(self):
        super(TestUnitModelPluginStep, self).setUp()
        self.ModelA = MagicMock()
        self.ModelB = MagicMock()
        self.step = publish_step.UnitModelPluginStep('mytype', [self.ModelA, self.ModelB],
                                                     repo=self.repo)

    @patch('pulp.server.controllers.repository.get_unit_model_querysets')
    def test_returns_querysets(self, mock_get_querysets):
        qs1 = MagicMock()
        qs2 = MagicMock()
        mock_get_querysets.side_effect = [[qs1], [qs2]]

        ret = self.step.unit_querysets

        self.assertEqual(ret, [qs1, qs2])

    @patch('pulp.server.controllers.repository.get_unit_model_querysets')
    def test_caches_querysets(self, mock_get_querysets):
        """
        make sure the values retrieved from get_unit_model_querysets are cached
        """
        qs1 = MagicMock()
        qs2 = MagicMock()
        mock_get_querysets.side_effect = [[qs1], [qs2]]

        self.step.unit_querysets
        self.step.unit_querysets
        self.step.unit_querysets
        self.step.unit_querysets
        self.step.unit_querysets

        self.assertEqual(mock_get_querysets.call_count, 2)

    def test_get_total(self):
        qs1 = MagicMock()
        qs1.count.return_value = 3
        qs2 = MagicMock()
        qs2.count.return_value = 4
        self.step._unit_querysets = [qs1, qs2]

        total = self.step.get_total()

        self.assertEqual(total, 7)

    def test_get_total_zero(self):
        self.step._unit_querysets = []

        total = self.step.get_total()

        self.assertEqual(total, 0)

    def test_get_iterator(self):
        u1 = MagicMock()
        u2 = MagicMock()
        u3 = MagicMock()
        self.step._unit_querysets = [[u1, u2], [u3]]

        ret = self.step.get_iterator()

        self.assertEqual(list(ret), [u1, u2, u3])


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

        value_list = [n.value for n in publish_step._post_order(n5)]
        self.assertEquals(value_list, [1, 2, 3, 4, 5])


class StepTests(PublisherBase):

    def test_add_child(self):
        step = publish_step.Step('foo')
        step2 = publish_step.Step('step2')
        step3 = publish_step.Step('step3')
        step.add_child(step2)
        step.add_child(step3)
        self.assertEquals(step.children, [step2, step3])

    def test_insert_child(self):
        step = publish_step.Step('foo')
        step2 = publish_step.Step('step2')
        step3 = publish_step.Step('step3')
        step4 = publish_step.Step('step4')
        step.add_child(step2)
        step.add_child(step3)
        step.insert_child(0, step4)
        self.assertEquals(step.children, [step4, step2, step3])

    def test_get_status_conduit(self):
        step = publish_step.Step('foo_step')
        step.status_conduit = 'foo'
        self.assertEquals('foo', step.get_status_conduit())

    def test_get_status_conduit_from_parent(self):
        step = publish_step.Step('foo_step')
        step.parent = Mock()
        step.parent.get_status_conduit.return_value = 'foo'
        self.assertEquals('foo', step.get_status_conduit())

    def test_get_total(self):
        step = publish_step.Step('foo_step')
        self.assertEquals(1, step.get_total())

    def test__get_total(self):
        step = publish_step.Step('foo_step')
        step.get_total = Mock(return_value=3)
        self.assertEquals(3, step._get_total())

    def test_report_progress_disable_reporting(self):
        """
        Test that we can disable reporting when calling report_progress()
        """
        step = publish_step.Step('foo_step', disable_reporting=True)
        step.status_conduit = Mock()
        step.report_progress()
        self.assertFalse(step.status_conduit.report_progress.called)


class TestStepProcessBlock(unittest.TestCase):
    def test_increments_progress(self):
        step = publish_step.Step('foo_step', disable_reporting=True)

        step._process_block()

        self.assertEqual(step.progress_successes, 1)

    def test_progress_overflow_prevention(self):
        step = publish_step.Step('foo_step', disable_reporting=True)
        # ensure the step still defaults to 1
        self.assertEqual(step.get_total(), 1)
        step.progress_successes = 1

        step._process_block()

        # make sure progress does not get incremented beyond the total
        self.assertEqual(step.progress_successes, 1)


class PluginStepTests(PluginBase):
    """
    This class has a lot of duplicated tests from PublishStepTests, in order to
    verify that the class has the same behavior before/after refactoring. After all
    the plugins are refactored to use the new PluginStep layout, the PublishStep tests
    can be removed.
    """

    def test_get_working_dir_from_step(self):
        """
        Test getting the working dir if it has already been calculated or set on this step
        """
        step = publish_step.PluginStep('foo_step')
        step.working_dir = 'foo'
        self.assertEquals('foo', step.get_working_dir())

    @patch('pulp.plugins.util.publish_step.common_utils.get_working_directory')
    def test_get_working_dir_from_util(self, mock_get_working_dir):
        """
        Test getting the working dir from the utilities
        """
        step = publish_step.PluginStep('foo_step')
        mock_get_working_dir.return_value = 'foo'
        self.assertEquals('foo', step.get_working_dir())

    def test_get_working_dir_from_parent(self):
        """
        Test getting the working dir from a parent step
        """
        step = publish_step.PluginStep('foo_step')
        step.parent = Mock(get_working_dir=Mock(return_value='foo'))
        self.assertEquals('foo', step.get_working_dir())

    def test_get_repo(self):
        step = publish_step.PluginStep('foo_step')
        step.repo = 'foo'
        self.assertEquals('foo', step.get_repo())

    def test_get_repo_from_parent(self):
        step = publish_step.PluginStep('foo_step')
        step.conduit = 'foo'
        step.parent = Mock()
        step.parent.get_repo.return_value = 'foo'
        self.assertEquals('foo', step.get_repo())

    def test_get_plugin_type(self):
        step = publish_step.PluginStep('foo_step')
        step.plugin_type = 'foo'
        self.assertEquals('foo', step.get_plugin_type())

    def test_get_plugin_type_none(self):
        step = publish_step.PluginStep('foo_step')
        self.assertEquals(None, step.get_plugin_type())

    def test_get_plugin_type_from_parent(self):
        step = publish_step.PluginStep('foo_step')
        step.conduit = 'foo'
        step.parent = Mock()
        step.parent.get_plugin_type.return_value = 'foo'
        self.assertEquals('foo', step.get_plugin_type())

    def test_get_conduit(self):
        step = publish_step.PluginStep('foo_step')
        step.conduit = 'foo'
        self.assertEquals('foo', step.get_conduit())

    def test_get_conduit_from_parent(self):
        step = publish_step.PluginStep('foo_step')
        step.conduit = 'foo'
        step.parent = Mock()
        step.parent.get_conduit.return_value = 'foo'
        self.assertEquals('foo', step.get_conduit())

    def test_get_conduit_not_set(self):
        """
        Test that if the conduit has not been set in this step or it's parent, that we
        return None
        """
        step = publish_step.PluginStep('foo_step')
        self.assertEquals(None, step.get_conduit())

    @patch('pulp.plugins.conduits.repo_publish.RepoPublishConduit.get_units')
    def test_process_step_failure_reported_on_metadata_finalized(self, mock_get_units):
        self.pluginstep.repo.content_unit_counts = {'FOO_TYPE': 1}
        mock_get_units.return_value = ['mock_unit']
        step = publish_step.PluginStep('foo_step')
        step.parent = self.pluginstep
        step.finalize = Mock(side_effect=Exception())
        self.assertRaises(Exception, step.process)
        self.assertEquals(step.state, reporting_constants.STATE_FAILED)
        self.assertEquals(step.progress_successes, 1)
        self.assertEquals(step.progress_failures, 1)
        self.assertEquals(step.total_units, 1)

    def test_cancel_before_processing(self):
        self.pluginstep.repo.content_unit_counts = {'FOO_TYPE': 2}
        step = publish_step.PluginStep('foo_step')
        step.is_skipped = Mock()
        step.cancel()
        step.process()
        self.assertEquals(0, step.is_skipped.call_count)

    def test_report_progress(self):
        plugin_step = publish_step.PluginStep('foo_step')
        plugin_step.parent = Mock()
        plugin_step.report_progress()
        plugin_step.parent.report_progress.assert_called_once_with(False)

    def test_record_failure(self):
        plugin_step = publish_step.PluginStep('foo_step')
        plugin_step.parent = self.pluginstep

        error_msg = 'Too bad, so sad'

        try:
            raise Exception(error_msg)

        except Exception, e:
            tb = sys.exc_info()[2]
            plugin_step._record_failure(e, tb)

        self.assertEquals(plugin_step.progress_failures, 1)
        details = {'error': str(e),
                   'traceback': '\n'.join(traceback.format_tb(tb))}
        self.assertEqual(plugin_step.error_details[0], details)

    def test_get_progress_report(self):
        step = publish_step.PluginStep('foo_step')
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
            reporting_constants.PROGRESS_DETAILS_KEY: '',
            reporting_constants.PROGRESS_STEP_UUID: step.uuid
        }

        compare_dict(report[0], target_report)

    def test_get_progress_report_description(self):
        step = publish_step.PluginStep('bar_step')
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
            reporting_constants.PROGRESS_DETAILS_KEY: '',
            reporting_constants.PROGRESS_STEP_UUID: step.uuid
        }

        compare_dict(report[0], target_report)

    def test_get_progress_report_summary(self):
        parent_step = publish_step.PluginStep('parent_step')
        step = publish_step.PluginStep('foo_step')
        parent_step.add_child(step)
        step.state = reporting_constants.STATE_COMPLETE
        report = parent_step.get_progress_report_summary()
        target_report = {
            'foo_step': reporting_constants.STATE_COMPLETE
        }
        compare_dict(report, target_report)

    def test_build_final_report_success(self):

        step_one = publish_step.PluginStep('step_one')
        step_one.state = reporting_constants.STATE_COMPLETE
        step_two = publish_step.PluginStep('step_two')
        step_two.state = reporting_constants.STATE_COMPLETE
        self.pluginstep.add_child(step_one)
        self.pluginstep.add_child(step_two)

        report = self.pluginstep._build_final_report()

        self.assertTrue(report.success_flag)

    def test_build_final_report_failure(self):

        self.pluginstep.state = reporting_constants.STATE_FAILED
        step_one = publish_step.PluginStep('step_one')
        step_one.state = reporting_constants.STATE_COMPLETE
        step_two = publish_step.PluginStep('step_two')
        step_two.state = reporting_constants.STATE_FAILED
        self.pluginstep.add_child(step_one)
        self.pluginstep.add_child(step_two)

        report = self.pluginstep._build_final_report()

        self.assertFalse(report.success_flag)

    def test_build_final_report_reporting_disable(self):
        """
        Test that _build_final_report returnes None if reporting has been disabled
        """
        step = publish_step.PluginStep('step_one', disable_reporting=True)
        report = step._build_final_report()
        self.assertEquals(report, None)

    def test_process_child_on_error_notifies_parent(self):
        # set working_dir and conduit. This is required by process_lifecycle
        step = publish_step.PluginStep('parent', working_dir=self.working_dir, conduit=self.conduit)
        child_step = publish_step.PluginStep(
            'child', working_dir=self.working_dir, conduit=self.conduit)
        child_step.initialize = Mock(side_effect=Exception('boo'))
        child_step.on_error = Mock(side_effect=Exception('flux'))
        step.on_error = Mock()

        step.add_child(child_step)

        self.assertRaises(Exception, step.process_lifecycle)

        self.assertEquals(reporting_constants.STATE_FAILED, step.state)
        self.assertEquals(reporting_constants.STATE_FAILED, child_step.state)
        self.assertTrue(step.on_error.called)
        self.assertTrue(child_step.on_error.called)

    def test_process_lifecycle(self):
        # set working_dir and conduit. This is required by process_lifecycle
        step = publish_step.PluginStep(
            'parent', working_dir=self.working_dir, conduit=self.conduit)
        step.process = Mock()
        child_step = publish_step.PluginStep(
            'child', working_dir=self.working_dir, conduit=self.conduit)
        child_step.process = Mock()
        step.add_child(child_step)
        step.report_progress = Mock()

        step.process_lifecycle()

        step.process.assert_called_once_with()
        child_step.process.assert_called_once_with()
        step.report_progress.assert_called_once_with(force=True)

    def test_process_lifecycle_reports_on_error(self):
        # set working_dir and conduit. This is required by process_lifecycle
        step = publish_step.PluginStep('parent', working_dir=self.working_dir, conduit=self.conduit)
        step.process = Mock(side_effect=Exception('Foo'))
        step.report_progress = Mock()

        self.assertRaises(Exception, step.process_lifecycle)

        step.report_progress.assert_called_once_with(force=True)

    def test_clear_children(self):
        step = publish_step.PublishStep("foo")
        step.children = ['bar']
        step.clear_children()
        self.assertEquals(0, len(step.children))


class PublishStepTests(PublisherBase):

    def test_get_distributor_type(self):
        step = publish_step.PublishStep('foo_step')
        step.plugin_type = 'foo'
        self.assertEquals('foo', step.get_distributor_type())

    def test_get_distributor_type_none(self):
        step = publish_step.PublishStep('foo_step')
        self.assertEquals(None, step.get_distributor_type())

    def test_get_distributor_type_from_parent(self):
        step = publish_step.PublishStep('foo_step')
        step.conduit = 'foo'
        step.parent = Mock()
        step.parent.get_plugin_type.return_value = 'foo'
        self.assertEquals('foo', step.get_distributor_type())

    @patch('pulp.plugins.util.misc.create_symlink')
    def test_create_symlink(self, mock_symlink):
        step = publish_step.PublishStep("foo")
        step._create_symlink('foo', 'bar')
        mock_symlink.assert_called_once_with('foo', 'bar')

    @patch('pulp.plugins.util.misc.clear_directory')
    def test_clear_directory(self, mock_clear):
        step = publish_step.PublishStep("foo")

        step._clear_directory(self.working_dir, ['two'])
        mock_clear.assert_called_once_with(self.working_dir, ['two'])

    def test_publish(self):
        # just test that process_lifecycle got called, that is where the functionality lives now
        step = publish_step.PublishStep("foo")
        step.process_lifecycle = Mock()
        step.publish()
        self.assertTrue(step.process_lifecycle.called)


class UnitPublishStepTests(PublisherBase):

    def _step_canceler(self, unit):
        if unit is 'cancel':
            self.publisher.cancel()

    def test_process_step_skip_units(self):
        self.publisher.config = PluginCallConfiguration(None, {'skip': ['FOO']})
        step = publish_step.UnitPublishStep('foo_step', 'FOO')
        step.parent = self.publisher
        step.process()
        self.assertEquals(step.state, reporting_constants.STATE_SKIPPED)

    @patch('pulp.plugins.conduits.repo_publish.RepoPublishConduit.get_units')
    def test_process_step_no_units(self, mock_get_units):
        self.publisher.repo.content_unit_counts = {'FOO_TYPE': 0}
        mock_method = Mock()
        mock_get_units.return_value = []
        step = publish_step.UnitPublishStep('foo_step', 'FOO_TYPE')
        step.parent = self.publisher
        step.process_unit = mock_method
        step.process()
        self.assertEquals(step.state, reporting_constants.STATE_COMPLETE)
        self.assertFalse(mock_method.called)

    @patch('pulp.plugins.conduits.repo_publish.RepoPublishConduit.get_units')
    def test_process_step_single_unit(self, mock_get_units):
        self.publisher.repo.content_unit_counts = {'FOO_TYPE': 1}
        mock_method = Mock()
        mock_get_units.return_value = ['mock_unit']
        step = publish_step.UnitPublishStep('foo_step', 'FOO_TYPE')
        step.parent = self.publisher
        step.process_unit = mock_method
        step.process()

        self.assertEquals(step.state, reporting_constants.STATE_COMPLETE)
        self.assertEquals(step.progress_successes, 1)
        self.assertEquals(step.progress_failures, 0)
        self.assertEquals(step.total_units, 1)
        mock_method.assert_called_once_with('mock_unit')

    @patch('pulp.plugins.conduits.repo_publish.RepoPublishConduit.get_units')
    def test_process_step_single_unit_exception(self, mock_get_units):
        self.publisher.repo.content_unit_counts = {'FOO_TYPE': 1}
        mock_method = Mock(side_effect=Exception())
        mock_get_units.return_value = ['mock_unit']
        step = publish_step.UnitPublishStep('foo_step', 'FOO_TYPE')
        step.parent = self.publisher
        step.process_unit = mock_method

        self.assertRaises(Exception, step.process)
        self.assertEquals(step.state, reporting_constants.STATE_FAILED)
        self.assertEquals(step.progress_successes, 0)
        self.assertEquals(step.progress_failures, 1)
        self.assertEquals(step.total_units, 1)
        mock_method.assert_called_once_with('mock_unit')

    @patch('pulp.plugins.conduits.repo_publish.RepoPublishConduit.get_units')
    def test_process_step_cancelled_mid_unit_processing(self, mock_get_units):
        self.publisher.repo.content_unit_counts = {'FOO_TYPE': 2}
        mock_get_units.return_value = ['cancel', 'bar_unit']
        step = publish_step.UnitPublishStep('foo_step', 'FOO_TYPE')
        self.publisher.add_child(step)

        step.process_unit = self._step_canceler
        step.process()

        self.assertEquals(step.state, reporting_constants.STATE_CANCELLED)
        self.assertEquals(step.progress_successes, 1)
        self.assertEquals(step.progress_failures, 0)
        self.assertEquals(step.total_units, 2)

    def test_is_skipped_list(self):
        step = publish_step.UnitPublishStep("foo", 'bar')
        step.config = PluginCallConfiguration(None, {'skip': ['bar', 'baz']})
        self.assertTrue(step.is_skipped())

    def test_is_skipped_dict(self):
        step = publish_step.UnitPublishStep("foo", 'bar')
        step.config = PluginCallConfiguration(None, {'skip': {'bar': True, 'baz': True}})
        self.assertTrue(step.is_skipped())

    def test_is_skipped_list_not_skipped(self):
        step = publish_step.UnitPublishStep("foo", 'bar')
        step.config = PluginCallConfiguration(None, None)
        self.assertFalse(step.is_skipped())

    def test_is_skipped_dict_not_skipped(self):
        step = publish_step.UnitPublishStep("foo", 'bar')
        step.config = PluginCallConfiguration(None, None)
        self.assertFalse(step.is_skipped())

    def test_get_total(self):
        step = publish_step.UnitPublishStep("foo", ['bar', 'baz'])
        step.parent = Mock()
        step.parent.repo.content_unit_counts.get.return_value = 1
        total = step._get_total()
        self.assertEquals(2, total)

    def test_get_total_for_list(self):
        step = publish_step.UnitPublishStep("foo", ['bar', 'baz'])
        step.parent = Mock()
        step.parent.repo.content_unit_counts.get.return_value = 1
        total = step._get_total()
        self.assertEquals(2, total)

    @patch('pulp.plugins.util.publish_step.manager_factory')
    def test_get_with_association_filter(self, mock_manager_factory):
        step = publish_step.UnitPublishStep("foo", ['bar', 'baz'])
        step.association_filters = {'foo': 'bar'}

        find_by_criteria = mock_manager_factory.repo_unit_association_query_manager.return_value.\
            find_by_criteria
        find_by_criteria.return_value.count.return_value = 5
        total = step._get_total()
        criteria_object = find_by_criteria.call_args[0][0]
        compare_dict(criteria_object.filters, {'foo': 'bar',
                                               'unit_type_id': {'$in': ['bar', 'baz']}})
        self.assertEquals(5, total)

    def test_get_total_ignore_filter(self):
        step = publish_step.UnitPublishStep("foo", ['bar', 'baz'])
        step.association_filters = {'foo': 'bar'}
        step.parent = Mock()
        step.parent.repo.content_unit_counts.get.return_value = 1
        total = step._get_total(ignore_filter=True)
        self.assertEquals(2, total)

    def test_get_total_for_none(self):
        step = publish_step.UnitPublishStep("foo", ['bar', 'baz'])
        step.parent = Mock()
        step.parent.repo.content_unit_counts.get.return_value = 0
        total = step._get_total()
        self.assertEquals(0, total)

    def test_process_unit_with_no_work(self):
        # Run the blank process unit to ensure no exceptions are raised
        step = publish_step.UnitPublishStep("foo", ['bar', 'baz'])
        step.process_main('foo')


class TestAtomicDirectoryPublishStep(unittest.TestCase):

    def setUp(self):
        self.working_directory = tempfile.mkdtemp()
        self.repo = Mock()

    def tearDown(self):
        shutil.rmtree(self.working_directory)

    def test_process_main_alternate_id(self):
        step = publish_step.AtomicDirectoryPublishStep('foo', 'bar', 'baz', step_type='alternate')
        self.assertEquals(step.step_id, 'alternate')

    def test_process_main_default_id(self):
        step = publish_step.AtomicDirectoryPublishStep('foo', 'bar', 'baz')
        self.assertEquals(step.step_id, reporting_constants.PUBLISH_STEP_DIRECTORY)

    def test_process_main(self):
        source_dir = os.path.join(self.working_directory, 'source')
        master_dir = os.path.join(self.working_directory, 'master')
        publish_dir = os.path.join(self.working_directory, 'publish', 'bar')
        publish_dir += '/'
        step = publish_step.AtomicDirectoryPublishStep(source_dir, [('/', publish_dir)], master_dir)
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

        step = publish_step.AtomicDirectoryPublishStep(
            source_dir, [('/', publish_dir), ('qux/quux.html', target_qux)], master_dir)
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
        step = publish_step.AtomicDirectoryPublishStep(
            source_dir, [('/', publish_dir)], master_dir, only_publish_directory_contents=True)
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
        step = publish_step.SaveTarFilePublishStep(source_dir, target_file)

        touch(os.path.join(source_dir, 'foo.txt'))
        step.process_main()

        with contextlib.closing(tarfile.open(target_file)) as tar_file:
            names = tar_file.getnames()
            # the first item is either '' or '.' depending on if this is py2.7 or py2.6
            self.assertEquals(names[1:], ['foo.txt'])


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

        step = publish_step.CopyDirectoryStep(source_dir, target_dir)

        touch(os.path.join(source_dir, 'foo.txt'))
        step.process_main()

        self.assertTrue(os.path.exists(target_file))


class DownloadStepTests(unittest.TestCase):

    TYPE_ID_FOO = 'foo'

    def get_basic_config(*arg, **kwargs):
        plugin_config = {"num_retries": 0, "retry_delay": 0}
        repo_plugin_config = {}
        for key in kwargs:
            repo_plugin_config[key] = kwargs[key]
        config = PluginCallConfiguration(plugin_config,
                                         repo_plugin_config=repo_plugin_config)
        return config

    def get_sync_conduit(type_id=None, existing_units=None, pkg_dir=None):
        def build_failure_report(summary, details):
            return SyncReport(False, sync_conduit._added_count, sync_conduit._updated_count,
                              sync_conduit._removed_count, summary, details)

        def build_success_report(summary, details):
            return SyncReport(True, sync_conduit._added_count, sync_conduit._updated_count,
                              sync_conduit._removed_count, summary, details)

        def side_effect(type_id, key, metadata, rel_path):
            if rel_path and pkg_dir:
                rel_path = os.path.join(pkg_dir, rel_path)
                if not os.path.exists(os.path.dirname(rel_path)):
                    os.makedirs(os.path.dirname(rel_path))
            unit = Unit(type_id, key, metadata, rel_path)
            return unit

        def get_units(criteria=None):
            ret_val = []
            if existing_units:
                for u in existing_units:
                    if criteria:
                        if u.type_id in criteria.type_ids:
                            ret_val.append(u)
                    else:
                        ret_val.append(u)
            return ret_val

        def search_all_units(type_id, criteria):
            ret_val = []
            if existing_units:
                for u in existing_units:
                    if u.type_id == type_id:
                        if u.unit_key['id'] == criteria['filters']['id']:
                            ret_val.append(u)
            return ret_val

        sync_conduit = Mock(spec=RepoSyncConduit)
        sync_conduit._added_count = sync_conduit._updated_count = sync_conduit._removed_count = 0
        sync_conduit.init_unit.side_effect = side_effect
        sync_conduit.get_units.side_effect = get_units
        sync_conduit.save_unit = Mock()
        sync_conduit.search_all_units.side_effect = search_all_units
        sync_conduit.build_failure_report = MagicMock(side_effect=build_failure_report)
        sync_conduit.build_success_report = MagicMock(side_effect=build_success_report)
        sync_conduit.set_progress = MagicMock()

        return sync_conduit

    def setUp(self):

        conf_dict = {
            importer_constants.KEY_FEED: 'http://fake.com/file_feed/',
            importer_constants.KEY_MAX_SPEED: 500.0,
            importer_constants.KEY_MAX_DOWNLOADS: 5,
            importer_constants.KEY_SSL_VALIDATION: False,
            importer_constants.KEY_SSL_CLIENT_CERT: "Trust me, I'm who I say I am.",
            importer_constants.KEY_SSL_CLIENT_KEY: "Secret Key",
            importer_constants.KEY_SSL_CA_CERT: "Uh, I guess that's the right server.",
            importer_constants.KEY_PROXY_HOST: 'proxy.com',
            importer_constants.KEY_PROXY_PORT: 1234,
            importer_constants.KEY_PROXY_USER: "the_dude",
            importer_constants.KEY_PROXY_PASS: 'bowling',
            importer_constants.KEY_VALIDATE: False,
        }
        self.real_config = self.get_basic_config(**conf_dict)
        self.real_conduit = self.get_sync_conduit()

        self.mock_repo = Mock()
        self.mock_conduit = Mock()
        self.mock_config = Mock()
        self.mock_working_dir = Mock()
        self.dlstep = publish_step.DownloadStep(
            "fake_download", repo=self.mock_repo, conduit=self.mock_conduit,
            config=self.mock_config, working_dir=self.mock_working_dir,
            plugin_type="fake plugin", description='foo')

    def test_init(self):
        self.assertEquals(self.dlstep.get_repo(), self.mock_repo)
        self.assertEquals(self.dlstep.get_conduit(), self.mock_conduit)
        self.assertEquals(self.dlstep.get_config(), self.mock_config)
        self.assertEquals(self.dlstep.get_working_dir(), self.mock_working_dir)
        self.assertEquals(self.dlstep.get_plugin_type(), "fake plugin")
        self.assertEqual(self.dlstep.description, 'foo')

    def test_initalize(self):
        # override mock config with real config dict
        self.dlstep.config = self.real_config
        self.dlstep.conduit = self.get_sync_conduit()

        self.dlstep.initialize()

        # Now let's assert that all the right things happened during initialization
        self.assertEqual(self.dlstep._repo_url, 'http://fake.com/file_feed/')
        # Validation of downloads should be disabled by default
        self.assertEqual(self.dlstep._validate_downloads, False)

        # Inspect the downloader
        downloader = self.dlstep.downloader
        # The dlstep should be the event listener for the downloader
        self.assertEqual(downloader.event_listener, self.dlstep)
        # Inspect the downloader config
        expected_downloader_config = {
            'max_speed': 500.0,
            'max_concurrent': 5,
            'ssl_client_cert': "Trust me, I'm who I say I am.",
            'ssl_client_key': 'Secret Key',
            'ssl_ca_cert': "Uh, I guess that's the right server.",
            'ssl_validation': False,
            'proxy_url': 'proxy.com',
            'proxy_port': 1234,
            'proxy_username': 'the_dude',
            'proxy_password': 'bowling'}
        for key, value in expected_downloader_config.items():
            self.assertEquals(getattr(downloader.config, key), value)

    def test__init___with_feed_lacking_trailing_slash(self):
        """
        tests https://bugzilla.redhat.com/show_bug.cgi?id=949004
        """
        slash_config = self.get_basic_config(
            **{importer_constants.KEY_FEED: 'http://fake.com/no_trailing_slash'})

        # override mock config with real config dict
        self.dlstep.config = slash_config
        self.dlstep.initialize()
        # Humorously enough, the _repo_url attribute named no_trailing_slash
        # should now have a trailing slash
        self.assertEqual(self.dlstep._repo_url, 'http://fake.com/no_trailing_slash/')

    def test__init___file_downloader(self):
        slash_config = self.get_basic_config(
            **{importer_constants.KEY_FEED: 'file:///some/path/'})
        # override mock config with real config dict
        self.dlstep.config = slash_config
        self.dlstep.initialize()
        self.assertTrue(isinstance(self.dlstep.downloader, LocalFileDownloader))

    def test__init___ssl_validation(self):
        """
        Make sure the SSL validation is on by default.
        """
        # It should default to True
        self.dlstep.config = self.get_basic_config(
            **{importer_constants.KEY_FEED: 'http://fake.com/iso_feed/'})
        self.dlstep.initialize()
        self.assertEqual(self.dlstep.downloader.config.ssl_validation, True)

        # It should be possible to explicitly set it to False
        self.dlstep.config = self.get_basic_config(
            **{importer_constants.KEY_FEED: 'http://fake.com/iso_feed/',
               importer_constants.KEY_SSL_VALIDATION: False})
        self.dlstep.initialize()
        self.assertEqual(self.dlstep.downloader.config.ssl_validation, False)

        # It should be possible to explicitly set it to True
        self.dlstep.config = self.get_basic_config(
            **{importer_constants.KEY_FEED: 'http://fake.com/iso_feed/',
               importer_constants.KEY_SSL_VALIDATION: True})
        self.dlstep.initialize()
        self.assertEqual(self.dlstep.downloader.config.ssl_validation, True)

    def test_get_total(self):
        mock_downloads = ['fake', 'downloads']
        dlstep = publish_step.DownloadStep('fake-step', downloads=mock_downloads)
        self.assertEquals(dlstep.get_total(), 2)

    def test_process_main(self):
        mock_downloader = Mock()
        mock_downloads = ['fake', 'downloads']
        dlstep = publish_step.DownloadStep('fake-step', downloads=mock_downloads)
        dlstep.downloader = mock_downloader
        dlstep.process_main()
        mock_downloader.download.assert_called_once_with(['fake', 'downloads'])

    def test_download_succeeded(self):
        dlstep = publish_step.DownloadStep('fake-step')
        mock_report = Mock()
        mock_report_progress = Mock()
        dlstep.report_progress = mock_report_progress
        dlstep.download_succeeded(mock_report)
        self.assertEquals(dlstep.progress_successes, 1)
        # assert report_progress was called with no args
        mock_report_progress.assert_called_once_with()

    def test_download_failed(self):
        dlstep = publish_step.DownloadStep('fake-step')
        mock_report = Mock()
        mock_report_progress = Mock()
        dlstep.report_progress = mock_report_progress
        dlstep.download_failed(mock_report)
        self.assertEquals(dlstep.progress_failures, 1)
        # assert report_progress was called with no args
        mock_report_progress.assert_called_once_with()

    def test_downloads_property(self):
        generator = (DownloadRequest(url, '/a/b/c') for url in ['http://pulpproject.org'])
        dlstep = publish_step.DownloadStep('fake-step', downloads=generator)

        downloads = dlstep.downloads

        self.assertTrue(isinstance(downloads, list))
        self.assertEqual(len(downloads), 1)
        self.assertTrue(isinstance(downloads[0], DownloadRequest))

    def test_cancel(self):
        dlstep = publish_step.DownloadStep('fake-step')
        dlstep.parent = MagicMock()
        dlstep.initialize()

        dlstep.cancel()

        self.assertTrue(dlstep.downloader.is_canceled)


@patch('pulp.plugins.util.publish_step.repo_controller.associate_single_unit')
@patch('pulp.plugins.util.publish_step.units_controller.find_units')
class TestGetLocalUnitsStep(unittest.TestCase):

    class DemoModel(model.ContentUnit):
        key_field = mongoengine.StringField()
        unit_key_fields = ['key_field']

        _content_type_id = 'demo_model'

        objects = MagicMock()
        save = MagicMock()

    def setUp(self):
        super(TestGetLocalUnitsStep, self).setUp()
        self.parent = MagicMock()
        fake_repo = Repository(id='fake-repo', repo_obj='fake_repo')
        self.step = publish_step.GetLocalUnitsStep('fake_importer_type', repo=fake_repo)
        self.step.parent = self.parent
        self.step.conduit = MagicMock()
        self.parent.available_units = []

    def test___init___default_available_units(self, find_units, associate):
        """
        Assert that the __init__() method correctly defaults to a value of None for the
        available_units parameter.
        """
        step = publish_step.GetLocalUnitsStep('fake_importer_type', repo='fake_repo')

        self.assertEqual(step.available_units, None)

    def test___init___with_available_units(self, find_units, associate):
        """
        Assert that the __init__() method allows the user to override the value of None for the
        available_units parameter.
        """
        available_units = ['unit1', 'unit2']

        step = publish_step.GetLocalUnitsStep('fake_importer_type', repo='fake_repo',
                                              available_units=available_units)

        self.assertEqual(step.available_units, available_units)

    def test_no_available_units(self, mock_find_units, mock_associate):
        self.step.process_main()

        self.assertEqual(self.step.conduit.save_unit.call_count, 0)
        self.assertEqual(self.step.units_to_download, [])

    @patch('pulp.plugins.util.publish_step.misc.paginate')
    def test_calls_get_multiple(self, mock_paginate, mock_find_units, mock_associate):
        """
        ensure that paginate is used
        """
        mock_paginate.return_value = []

        self.step.process_main()

        mock_paginate.assert_called_once_with(self.step.parent.available_units, 50)

    def test_saves_unit(self, mock_find_units, mock_associate):
        """
        Test that units which already exist in the database are associated properly
        """
        demo = self.DemoModel(key_field='a')
        self.parent.available_units = [demo]
        existing_demo = self.DemoModel(key_field='a', id='foo')
        mock_find_units.return_value = [existing_demo]

        self.step.process_main()
        mock_associate.assert_called_once_with('fake_repo', existing_demo)
        mock_find_units.assert_called_once_with((demo, ))

        # Ensure that the unit was not marked for download
        self.assertEqual(self.step.units_to_download, [])

    def test_populates_units_to_download(self, mock_find_units, mock_associate):
        """
        Test that if a unit does not exist in the database it is added to the
        units_to_download list. This test also tests the case when the step is not constructed with
        an available_units parameter that the parent step's available units is used.
        """
        demo_1 = self.DemoModel(key_field='a')
        demo_2 = self.DemoModel(key_field='b')
        self.parent.available_units = [demo_1, demo_2]
        existing_demo = self.DemoModel(key_field='b', id='foo')
        mock_find_units.return_value = [existing_demo]

        self.step.process_main()
        mock_find_units.assert_called_once_with((demo_1, demo_2))

        # the one that exists is associated
        mock_associate.assert_called_once_with('fake_repo', existing_demo)
        # the one that does not exist yet is added to the download list
        self.assertEqual(self.step.units_to_download, [demo_1])

    def test_uses_passed_available_units_when_requested(self, mock_find_units, mock_associate):
        """
        Assert that if the step is constructed with available_units passed in, the step's parent's
        available_units attribute is ignored.
        """
        demo_1 = self.DemoModel(key_field='a')
        demo_2 = self.DemoModel(key_field='b')
        demo_3 = self.DemoModel(key_field='c')
        self.parent.available_units = [demo_1, demo_2]
        available_units = [demo_1, demo_2, demo_3]
        fake_repo = Repository(id='fake-repo', repo_obj='fake_repo')
        step = publish_step.GetLocalUnitsStep('fake_importer_type', repo=fake_repo,
                                              available_units=available_units)
        step.parent = self.parent
        step.conduit = MagicMock()
        existing_demo = self.DemoModel(key_field='b', id='foo')
        mock_find_units.return_value = [existing_demo]

        step.process_main()

        # The parent step's available units only has demo 1 and 2, so this asserts that that is
        # being ignored and the correct available_units is being used instead.
        mock_find_units.assert_called_once_with((demo_1, demo_2, demo_3))
        # the one that exists is associated
        mock_associate.assert_called_once_with('fake_repo', existing_demo)
        # the two that do not exist yet are added to the download list
        self.assertEqual(step.units_to_download, [demo_1, demo_3])

    def test_empty_available_units(self, mock_find_units, mock_associate):
        """
        Assert that if the step is constructed with the an empty available_units passed in, the
        step's parent's available_units attribute is ignored.
        """
        demo_1 = self.DemoModel(key_field='a')
        self.parent.available_units = [demo_1]
        fake_repo = Repository(id='fake-repo', repo_obj='fake_repo')
        step = publish_step.GetLocalUnitsStep('fake_importer_type', repo=fake_repo,
                                              available_units=[])
        step.parent = self.parent
        step.conduit = MagicMock()
        existing_demo = self.DemoModel(key_field='b', id='foo')
        mock_find_units.return_value = [existing_demo]

        step.process_main()

        # The parent step's available units only has demo 1 and 2, so this asserts that that is
        # being ignored and the correct available_units is being used instead.
        self.assertEqual(mock_find_units.call_count, 0)


class TestSaveUnitsStep(unittest.TestCase):

    @patch('pulp.plugins.util.publish_step.repo_controller')
    def test_finalize(self, mock_repo_controller):
        repo = Repository('repo1')
        repo.repo_obj = model.Repository(repo_id=repo.id)
        step = publish_step.SaveUnitsStep('foo_type', repo=repo)
        step.finalize()
        mock_repo_controller.rebuild_content_unit_counts.assert_called_once_with(repo.repo_obj)


class TestCreateManifestStep(unittest.TestCase):
    def test_init(self):
        step = publish_step.CreatePulpManifestStep('/foo')

        # make sure the description has some value
        self.assertTrue(step.description)

    @patch('pulp.plugins.util.manifest_writer.make_manifest_for_dir', spec_set=True)
    def test_process_main(self, mock_make_manifest):
        step = publish_step.CreatePulpManifestStep('/foo/')

        step.process_main()

        mock_make_manifest.assert_called_once_with('/foo/')
