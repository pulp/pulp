"""
Contains a generic renderer for use printing status for tasks created with the
pulp.plugins.util.publish_step.BasePublisher & PublishStep.
"""
from gettext import gettext as _

from pulp.client.commands.repo.sync_publish import StatusRenderer
from pulp.common.plugins import reporting_constants


class CancelException(Exception):
    pass


class StepInfo(object):
    """
    Helper structure for storing information about steps in progress
    """

    def __init__(self):
        self.state = reporting_constants.STATE_NOT_STARTED
        self.spinner = None
        self.initialized = False
        self.total = 1
        self.done = False


class PublishStepStatusRenderer(StatusRenderer):
    def __init__(self, context):
        super(PublishStepStatusRenderer, self).__init__(context)
        self.steps = {}

    def display_report(self, progress_report):
        """
        Displays the contents of the progress report to the user. This will
        aggregate the calls to render individual sections of the report.

        :param progress_report: A standard progress report from the conduit
        :type progress_report: dict
        """

        # There's a small race condition where the task will indicate it's
        # begun running but the importer has yet to submit a progress report
        # (or it has yet to be saved into the task). This should be alleviated
        # by the if statements below.
        try:
            # The conduit returns a structure of {'distributor_type': [reports] }
            # We can ignore the distributor type and just get the first item in the dictionary
            if progress_report:
                reports = progress_report.values()[0]
                for report_details in reports:
                    self.render_step(report_details)
        except CancelException:
            self.prompt.render_failure_message(_('Operation cancelled.'))

    def render_step(self, step_details):
        """
        Render the details of a specific step.  If the step is in progress already the displayed
        output will be updated with the current state.

        :param step_details: The detailed report for this specific step
        :type step_details: dict
        """
        if not step_details:
            return

        step_id = step_details[reporting_constants.PROGRESS_STEP_UUID]
        current_state = step_details[reporting_constants.PROGRESS_STATE_KEY]

        if current_state == reporting_constants.STATE_CANCELLED:
            raise CancelException
        elif current_state == reporting_constants.STATE_NOT_STARTED \
                or step_details[reporting_constants.PROGRESS_DESCRIPTION_KEY] == '':
            return

        step = self.steps.get(step_id)
        if not step:
            step = StepInfo()
            self.steps[step_id] = step
            step.total = step_details[reporting_constants.PROGRESS_ITEMS_TOTAL_KEY]

        if current_state in reporting_constants.FINAL_STATES and step.done:
            return

        step.processed = step_details[reporting_constants.PROGRESS_NUM_PROCESSED_KEY]
        step.details = step_details[reporting_constants.PROGRESS_DETAILS_KEY]
        if not step.details:
            step.details = None

        if not step.initialized \
                and current_state != reporting_constants.STATE_NOT_STARTED:
            self.prompt.write(step_details[reporting_constants.PROGRESS_DESCRIPTION_KEY])
            if step.total > 1:
                step.progress_bar = self.prompt.create_progress_bar()
            else:
                step.spinner = self.prompt.create_spinner()
            step.initialized = True

        if current_state == reporting_constants.STATE_SKIPPED:
            self.prompt.write(_('... skipped'))
            self.prompt.render_spacer()
            step.state = current_state
            step.done = True
            return

        if step.total > 1:
            if step.details:
                template = _("%s of %s items: %s")
                message = template % (step.processed, step.total, step.details)
            else:
                template = _("%s of %s items")
                message = template % (step.processed, step.total)

            step.progress_bar.render(step.processed, step.total, message=message)
        else:
            if current_state in reporting_constants.FINAL_STATES:
                step.spinner.next(finished=True, message=step.details)
                step.done = True
            else:
                step.spinner.next(message=step.details)

        if current_state != step.state:
            if current_state == reporting_constants.STATE_COMPLETE:
                step.done = True
                self.prompt.write(_('... completed'))
                self.prompt.render_spacer()
            elif current_state == reporting_constants.STATE_FAILED:
                self.prompt.write(_('... failed'))
                step.done = True
                error_details = step_details[reporting_constants.PROGRESS_ERROR_DETAILS_KEY]
                for error_detail in error_details:
                    self.prompt.render_failure_message(error_detail['error'])

        step.state = current_state
