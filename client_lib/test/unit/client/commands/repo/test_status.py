import unittest
from mock import Mock

from pulp.common.plugins import reporting_constants
from pulp.client.commands.repo import status


class TestPublishStepStatusRenderer(unittest.TestCase):

    def setUp(self):
        self.context = Mock()
        self.prompt = Mock()
        self.context.prompt = self.prompt
        self.renderer = status.PublishStepStatusRenderer(self.context)
        self.step = {
            reporting_constants.PROGRESS_STEP_TYPE_KEY: u'foo_step',
            reporting_constants.PROGRESS_STEP_UUID: u'abcde',
            reporting_constants.PROGRESS_DESCRIPTION_KEY: u'foo description',
            reporting_constants.PROGRESS_DETAILS_KEY: u'bar details',
            reporting_constants.PROGRESS_STATE_KEY: reporting_constants.STATE_NOT_STARTED,
            reporting_constants.PROGRESS_ITEMS_TOTAL_KEY: 1,
            reporting_constants.PROGRESS_NUM_PROCESSED_KEY: 0,
            reporting_constants.PROGRESS_ERROR_DETAILS_KEY: []
        }

    def get_report(self):
        return {u'foo_id': self.step}

    def test_render_step_none(self):
        self.step = None
        self.renderer.render_step(self.step)
        self.assertFalse(self.prompt.called)

    def test_render_step_cancel(self):
        self.step[reporting_constants.PROGRESS_STATE_KEY] = reporting_constants.STATE_CANCELLED
        self.assertRaises(status.CancelException, self.renderer.render_step, self.step)
        self.assertFalse(self.prompt.called)

    def test_render_step_not_started(self):
        self.step[reporting_constants.PROGRESS_STATE_KEY] = reporting_constants.STATE_NOT_STARTED
        self.renderer.render_step(self.step)
        self.assertFalse(self.prompt.called)

    def test_render_step_empty_description(self):
        self.step[reporting_constants.PROGRESS_DESCRIPTION_KEY] = u''
        self.renderer.render_step(self.step)
        self.assertFalse(self.prompt.called)

    def test_render_step_working(self):
        self.step[reporting_constants.PROGRESS_STATE_KEY] = reporting_constants.STATE_RUNNING
        self.renderer.render_step(self.step)

        step = self.renderer.steps[self.step[reporting_constants.PROGRESS_STEP_UUID]]
        self.assertTrue(step.spinner.next.called)
        self.assertEquals(step.state, reporting_constants.STATE_RUNNING)

    def test_render_step_working_with_progress_bar(self):
        self.step[reporting_constants.PROGRESS_STATE_KEY] = reporting_constants.STATE_RUNNING
        self.step[reporting_constants.PROGRESS_ITEMS_TOTAL_KEY] = 50
        self.step[reporting_constants.PROGRESS_NUM_SUCCESSES_KEY] = 5
        self.renderer.render_step(self.step)

        step = self.renderer.steps[self.step[reporting_constants.PROGRESS_STEP_UUID]]
        self.assertTrue(step.progress_bar.render.called)
        self.assertEquals(step.state, reporting_constants.STATE_RUNNING)

    def test_render_step_finished(self):
        self.step[reporting_constants.PROGRESS_STATE_KEY] = reporting_constants.STATE_COMPLETE
        self.renderer.render_step(self.step)

        step = self.renderer.steps[self.step[reporting_constants.PROGRESS_STEP_UUID]]
        step.spinner.next.assert_called_once_with(message=u'bar details', finished=True)
        self.assertEquals(step.state, reporting_constants.STATE_COMPLETE)

    def test_render_step_skipped(self):
        self.step[reporting_constants.PROGRESS_STATE_KEY] = reporting_constants.STATE_SKIPPED
        self.renderer.render_step(self.step)

        step = self.renderer.steps[self.step[reporting_constants.PROGRESS_STEP_UUID]]
        self.assertEquals(step.state, reporting_constants.STATE_SKIPPED)
        self.assertTrue(step.done)

    def test_render_step_failed(self):
        self.step[reporting_constants.PROGRESS_STATE_KEY] = reporting_constants.STATE_FAILED
        self.step[reporting_constants.PROGRESS_ERROR_DETAILS_KEY].append({'error': 'foo'})
        self.renderer.render_step(self.step)

        step = self.renderer.steps[self.step[reporting_constants.PROGRESS_STEP_UUID]]
        self.assertTrue(step.done)
        self.assertEquals(step.state, reporting_constants.STATE_FAILED)
        self.prompt.render_failure_message.assert_called_once_with('foo')

    def test_render_step_double_call_done(self):
        """
        Test to ensure that a second call to render after a step has finished does not add
        any output.
        """
        self.step[reporting_constants.PROGRESS_STATE_KEY] = reporting_constants.STATE_COMPLETE
        self.renderer.render_step(self.step)

        step = self.renderer.steps[self.step[reporting_constants.PROGRESS_STEP_UUID]]

        step.spinner.next.reset_mock()
        self.renderer.render_step(self.step)
        self.assertFalse(step.spinner.next.called)

    def test_display_report_none(self):
        self.renderer.render_step = Mock()
        self.renderer.display_report(None)
        self.assertFalse(self.renderer.render_step.called)

    def test_display_report_empty(self):
        self.renderer.render_step = Mock()
        self.renderer.display_report({})
        self.assertFalse(self.renderer.render_step.called)

    def test_display_report_value(self):
        self.renderer.render_step = Mock()
        self.renderer.display_report({'foo': ['bar']})
        self.renderer.render_step.assert_called_once_with('bar')

    def test_display_report_canceled(self):
        self.renderer.render_step = Mock(side_effect=status.CancelException())
        self.renderer.display_report({'foo': ['bar']})
        self.assertTrue(self.prompt.render_failure_message.called)
