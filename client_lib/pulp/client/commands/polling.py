"""
Contains base classes for commands that poll the server for asynchronous tasks.
"""

import time
from gettext import gettext as _

from pulp.client.extensions.extensions import PulpCliCommand, PulpCliFlag
from pulp.bindings.responses import Task

# Returned from the poll command if one or more of the tasks in the given list
# was rejected
RESULT_REJECTED = 'rejected'

# Returned from the poll command if the user gracefully aborts the polling
RESULT_ABORTED = 'aborted'

# Returned from the poll command if the user elects to not poll the task
RESULT_BACKGROUND = 'background'

DESC_BACKGROUND = _('if specified, the client process will end immediately (the task will '
                    'continue to run on the server)')
FLAG_BACKGROUND = PulpCliFlag('--bg', DESC_BACKGROUND)


class PollingCommand(PulpCliCommand):
    """
    Base class for commands that wish to track a task executed on the server.
    Subclasses should override the rendering methods as appropriate to display
    custom messages based on the task state or progress.

    If the poll_frequency_in_seconds is not specified, it will be loaded from
    the configuration under output -> poll_frequency_in_seconds.

    :ivar context: the client context
    :type context: pulp.client.extensions.core.ClientContext
    """

    def __init__(self, name, description, method, context, poll_frequency_in_seconds=None):
        """
        :param name: command name
        :type  name: str
        :param description: command description
        :type  description: str
        :param method: method that will be fun when the command is invoked
        :type  method: function
        :param context: client context
        :type  context: pulp.client.extensions.core.ClientContext
        :param poll_frequency_in_seconds: time between polling calls to the server
        :type  poll_frequency_in_seconds: float
        """
        PulpCliCommand.__init__(self, name, description, method)
        self.context = context
        self.prompt = context.prompt

        self.poll_frequency_in_seconds = poll_frequency_in_seconds
        if poll_frequency_in_seconds is None:
            self.poll_frequency_in_seconds = float(
                self.context.config['output']['poll_frequency_in_seconds']
            )

        self.add_flag(FLAG_BACKGROUND)

        # list of tasks we already know about
        self.known_tasks = set()

    def poll(self, task_list, user_input):
        """
        Entry point to begin polling on the tasks in the given list. Each task will be polled
        in order until completion. If an error state is encountered, polling of the remaining
        tests will be stopped.

        This method is intended to handle all task states, from waiting to rejected. The
        appropriate message method below will be called depending on the state encounteres.
        Subclasses should override these methods as necessary to customize the message displayed.

        While each task is being polled, the progress method will be called at regular
        intervals to allow the subclass to display information on the state of the task.

        The command has a built in flag for running the process in the background. If this
        is specified, this method will immediately return and not poll the tasks.

        The typical returned value from this call is the final list of completed tasks.
        There are a few cases where this list is unavailable, in which case the RESULT_*
        constants in this module will be returned.

        :param task_list: list or single task report(s) received from the initial call to the server
        :type  task_list: list of or a single pulp.bindings.responses.Task

        :param user_input: keyword arguments that was passed to the command's method; these contain
                           the user-specified options that may affect this method
        :type  user_input: dict

        :return: the final task reports for all of the tasks
        """

        # Process the task_list to get the items we actually care about
        task_list = self._get_tasks_to_poll(task_list)

        # I'm not sure the server has the potential to return an empty list of tasks if nothing
        # was queued, but in case it does account for it here so the caller doesn't have to
        # check anything about the task list before calling this.
        if len(task_list) == 0:
            return []

        # Punch out early if polling is disabled. This should be done after the rejected check
        # since the expectation is that the tasks were successfully queued but aren't being watched.
        if user_input.get(FLAG_BACKGROUND.keyword, False):
            self.background()
            return RESULT_BACKGROUND

        msg = _('This command may be exited via ctrl+c without affecting the request.')
        self.prompt.render_paragraph(msg, tag='abort')

        try:
            # Keep a copy of the final reports for all tasks to return to the caller
            completed_task_list = []

            for task in task_list:
                task = self._poll_task(task)

                # If there are more than one tasks to poll, we need to display a divider so
                # the user knows which task is being followed.
                if len(task_list) > 1:
                    self.task_header(task)

                # Look for new tasks that we need to start polling for
                task_list.extend(self._get_tasks_to_poll(task))

                completed_task_list.append(task)

                # Display the appropriate message based on the result of the task
                self.prompt.render_spacer(1)
                if task.was_successful():
                    self.succeeded(task)

                if task.was_failure():
                    self.failed(task)
                    # Check for the error_message in the task_result generically
                    # so individual handlers don't have to process it.
                    if task and task.result and 'error_message' in task.result:
                        self.context.prompt.render_failure_message(task.result['error_message'])
                    break

                if task.was_cancelled():
                    self.cancelled(task)
                    break

                self.prompt.render_spacer(1)

            return completed_task_list

        except KeyboardInterrupt:
            # Gracefully handle if the user aborts the polling.
            return RESULT_ABORTED

    def _get_tasks_to_poll(self, task):
        """
        Recursively run through the tasks returned and add them to the list of
        items to be processed if and only if they have a task_id

        :param task: A single or a list of tasks
        :type task: list or pulp.bindings.responses.Task
        :returns: list of tasks to poll
        :rtype list of list or pulp.bindings.responses.Task
        """
        result_list = []
        if isinstance(task, list):
            for item in list(task):
                result_list.extend(self._get_tasks_to_poll(item))
        elif isinstance(task, Task):
            # This isn't an list of tasks but that's ok, we will see if it is an individual task
            if task.task_id and task.task_id not in self.known_tasks:
                self.known_tasks.add(task.task_id)
                result_list.append(task)
            for item in task.spawned_tasks:
                result_list.extend(self._get_tasks_to_poll(item))
        else:
            raise TypeError('task is not an list or a Task')

        return result_list

    def _poll_task(self, task):
        """
        Handles a specific task in the task list until it has completed. This call will handle
        displaying messages while the task is in the waiting state and making progress callbacks
        into the progress method.

        :param task: A queued task.
        :type  task: pulp.bindings.responses.Task

        :return: the completed task report
        :rtype:  pulp.bindings.responses.Task
        """
        delayed_spinner = self.context.prompt.create_spinner()
        delayed_spinner.spin_tag = 'delayed-spinner'
        running_spinner = self.context.prompt.create_spinner()
        running_spinner.spin_tag = 'running-spinner'

        first_run = True
        while not task.is_completed():

            if task.is_waiting():
                self.waiting(task, delayed_spinner)
            elif task.was_accepted():
                self.accepted(task, delayed_spinner)
            else:
                if first_run:
                    self.prompt.render_spacer(1)
                    first_run = False
                self.progress(task, running_spinner)

            time.sleep(self.poll_frequency_in_seconds)

            response = self.context.server.tasks.get_task(task.task_id)
            task = response.response_body

        # One final call to update the progress with the end state. It's possible the run state
        # was never hit in the loop above, so we check for first_run again for the missing blank
        # space.
        if first_run:
            self.prompt.render_spacer(1)

        self.progress(task, running_spinner)

        return task

    def task_header(self, task):
        """
        Displays information to the user to indicate which task is about to be tracked.
        This is only called once per task immediately before the polling loop begins and
        only if there is more than one task being tracked.

        The default implementation is less user-friendly than many of these render method
        implementations. Typical overridden implementations should check the tags on the task
        and use that to display a user-friendly message about which task is taking place.

        :param task: task about to be polled
        :type  task: pulp.bindings.responses.Task
        """
        template = _('-- Task Tags: %(tags)s ----')
        msg = template % {'tags': ', '.join(task.tags)}
        self.prompt.render_paragraph(msg, tag='header')

    def waiting(self, task, spinner):
        """
        Called while an accepted task (i.e. not postponed) is waiting to begin.
        Subclasses may override this to return a custom message to the user.

        :param task: full task report for the task being displayed
        :type  task: pulp.bindings.responses.Task

        :param spinner: used to indicate progress is still taking place
        :type  spinner: okaara.progress.Spinner
        """
        msg = _('Waiting to begin...')
        spinner.next(msg)

    def accepted(self, task, spinner):
        """
        Called when a task has been accepted.
        Subclasses may override this to display a custom message to the user.

        :param task: full task report for the task being displayed
        :type  task: pulp.bindings.responses.Task

        :param spinner: used to indicate progress is still taking place
        :type  spinner: okaara.progress.Spinner
        """
        msg = _('Accepted...')
        spinner.next(message=msg)

    def progress(self, task, spinner):
        """
        Called each time a task is polled. The default implementation displays nothing.
        The provided spinner may be used to indicate progress has taken place or may be ignored
        and replaced with an alternate solution in the subclass.

        :param task: full task report for the task being displayed
        :type  task: pulp.bindings.responses.Task

        :param spinner: used to indicate progress is still taking place
        :type  spinner: okaara.progress.Spinner
        """
        msg = _('Running...')
        spinner.next(message=msg)

    def succeeded(self, task):
        """
        Called when a task has completed with a status indicating success.
        Subclasses may override this to display a custom message to the user.

        :param task: full task report for the task being displayed
        :type  task: pulp.bindings.responses.Task
        """
        msg = _('Task Succeeded')
        self.prompt.render_success_message(msg, tag='succeeded')

    def failed(self, task):
        """
        Called when a task has completed with a status indicating that it failed.
        Subclasses may override this to display a custom message to the user.

        :param task: full task report for the task being displayed
        :type  task: pulp.bindings.responses.Task
        """
        msg = _('Task Failed')
        self.prompt.render_failure_message(msg, tag='failed')
        if task and task.exception:
            self.prompt.render_failure_message(task.exception, tag='failed_exception')
        elif task and task.error and 'description' in task.error:
            self.context.prompt.render_failure_message(task.error['description'],
                                                       tag='error_message')

    def cancelled(self, task):
        """
        Called when a task has completed with a status indicating that it was cancelled.
        Subclasses may override this to display a custom message to the user.

        :param task: full task report for the task being displayed
        :type  task: pulp.bindings.responses.Task
        """
        msg = _('Task Cancelled')
        self.prompt.render_paragraph(msg, tag='cancelled')

    def rejected(self, task):
        """
        Called in the event the task list indicates the request was rejected.
        Subclasses may override this to display a custom message to the user.

        :param task: full task report for the task being displayed
        :type  task: pulp.bindings.responses.Task
        """
        msg = _('The request was rejected by the server. '
                'This is likely due to an impending delete request for the resource.')
        self.context.prompt.render_failure_message(msg, tag='rejected')

    def background(self):
        """
        Called when the command is run with the background flag, effectively
        skipping polling entirely. The intention of this call is to display a message to
        the user informing them the task will continue on the server, but subclasses may
        elect to have this method display nothing.
        """
        msg = _('The request has been queued on the server.')
        self.context.prompt.render_paragraph(msg, tag='background')
