from gettext import gettext as _

import pulp.common.tags as tag_utils
from pulp.bindings.exceptions import PulpServerException
from pulp.client import parsers
from pulp.client.extensions.extensions import PulpCliSection, PulpCliFlag, PulpCliOption


# Guidance for render_document_list on how to display task info
TASK_DETAILS_DOC_ORDER = ['operations', 'resources', 'state', 'start_time', 'finish_time',
                          'result', 'task_id']
TASK_LIST_DOC_ORDER = ['operations', 'resources', 'state', 'start_time', 'finish_time', 'task_id']


def initialize(context):
    # Add root level section for all tasks in Pulp
    all_tasks_section = AllTasksSection(context, 'tasks', _('list and cancel server-side tasks'))
    context.cli.add_section(all_tasks_section)

    # Add repo level section for only repo tasks
    repo_tasks_section = RepoTasksSection(context, 'tasks', _(
        'list and cancel tasks related to a specific repository')
    )
    repo_section = context.cli.find_section('repo')
    repo_section.add_subsection(repo_tasks_section)


class BaseTasksSection(PulpCliSection):
    """
    Base class for handling tasks in the Pulp server. This should be subclassed
    to provide consistent functionality for a subset of tasks.
    """

    all_flag = PulpCliFlag('--all', _('if specified, all tasks in all states are shown'),
                           aliases=['-a'])
    state_option = PulpCliOption('--state',
                                 _('comma-separated list of tasks states desired to be '
                                   'shown. Example: "running,waiting,canceled,successful,failed". '
                                   'Do not include spaces'), aliases=['-s'], required=False,
                                 parse_func=parsers.csv)

    def __init__(self, context, name, description):
        PulpCliSection.__init__(self, name, description)
        self.context = context

        # Store the command instances as instance variables so the subclasses
        # can manipulate them if necessary

        self.list_command = self.create_command(
            'list', _('lists tasks queued (waiting) or running on the server'), self.list
        )

        self.cancel_command = self.create_command('cancel', _('cancel one or more tasks'),
                                                  self.cancel)
        self.cancel_command.create_option('--task-id', _('identifies the task to cancel'),
                                          required=True)

        self.details_command = self.create_command('details', _(
            'displays more detailed information about a specific task'), self.details
        )
        self.details_command.create_option('--task-id', _('identifies the task'), required=True)

    def list(self, **kwargs):
        """
        Displays a list of tasks. The list of tasks is driven by the
        retrieve_tasks method which should be overridden to provide the
        correct behavior.
        """

        self.context.prompt.render_title('Tasks')

        if kwargs.get(self.all_flag.keyword) and kwargs.get(self.state_option.keyword):
            msg = _('These arguments cannot be used together')
            self.context.prompt.render_failure_message(msg)
            return

        task_objects = self.retrieve_tasks(**kwargs)

        # Easy out clause
        if len(task_objects) is 0:
            self.context.prompt.render_paragraph('No tasks found')
            return

        # Parse each task object into a document to be displayed using the
        # prompt utilities
        task_documents = []
        for task in task_objects:
            # Interpret task values
            state, start_time, finish_time, result = self.parse_state(task)
            actions, resources = self.parse_tags(task)

            task_doc = {
                'operations': ', '.join(actions),
                'resources': ', '.join(resources),
                'task_id': task.task_id,
                'state': state,
                'start_time': start_time,
                'finish_time': finish_time,
            }
            task_documents.append(task_doc)

        self.context.prompt.render_document_list(task_documents, order=TASK_LIST_DOC_ORDER)

    def details(self, **kwargs):
        """
        Displays detailed information about a single task. The task ID must
        be in kwargs under "task-id".
        """
        self.context.prompt.render_title('Task Details')

        task_id = kwargs['task-id']
        response = self.context.server.tasks.get_task(task_id)
        task = response.response_body

        # Interpret task values
        state, start_time, finish_time, result = self.parse_state(task)
        actions, resources = self.parse_tags(task)

        # Assemble document to be displayed
        task_doc = {
            'operations': ', '.join(actions),
            'resources': ', '.join(resources),
            'task_id': task.task_id,
            'state': state,
            'start_time': start_time,
            'finish_time': finish_time,
            'result': result,
            'progress_report': task.progress_report,
        }

        if task.exception:
            task_doc['exception'] = task.exception

        if task.traceback:
            task_doc['traceback'] = task.traceback

        self.context.prompt.render_document(task_doc, order=TASK_DETAILS_DOC_ORDER)

    def cancel(self, **kwargs):
        """
        Attempts to cancel a task. Only unstarted tasks and those that support
        cancellation (sync, publish) can be canceled. If a task does not support
        cancelling, a not implemented error (501) will be raised from the server.
        We should handle that gracefully to explain to the user what happend.
        Otherwise, all other errors should bubble up to the exception middleware
        as usual.
        """

        task_id = kwargs['task-id']

        try:
            self.context.server.tasks.cancel_task(task_id)
            self.context.prompt.render_success_message(_('Task cancel is successfully initiated.'))
        except PulpServerException, e:

            # A 501 has a bit of a special meaning here that's not used in the
            # exception middleware, so handle it here.
            if e.http_status == 501:
                msg = _('The requested task does not support cancellation.')
                self.context.prompt.render_failure_message(msg)
                return
            else:
                raise

    @staticmethod
    def parse_state(task):
        """
        Uses the state of the task to return user-friendly descriptions of the
        state and task timing values.

        @param task: object representation of the task
        @type  task: Task

        @return: tuple of state, start time, finish time, and result
        @rtype: (str, str, str, str)
        """

        state = _('Unknown')
        result = _('Unknown')
        start_time = task.start_time or _('Unstarted')
        finish_time = task.finish_time or _('Incomplete')

        if task.is_waiting():
            state = _('Waiting')
            result = _('Incomplete')
        elif task.is_running():
            state = _('Running')
            result = _('Incomplete')
        elif task.is_completed():
            if task.was_successful():
                state = _('Successful')
                # Use the result value or pretty text if there was none
                result = task.result or _('N/A')
            elif task.was_failure():
                state = _('Failed')
                result = task.result or _('N/A')
            elif task.was_skipped():
                state = _('Skipped')
                start_time = _('N/A')
                finish_time = _('N/A')
                result = _('N/A')
            elif task.was_cancelled():
                state = _('Canceled')
                result = _('N/A')

        return state, start_time, finish_time, result

    @staticmethod
    def parse_tags(task):
        """
        Uses the tags entry in the task to render a user-friendly display of
        the actions and resources involved in the task.

        @param task: object representation of the task
        @type  task: Task

        @return: tuple of list of actions and list of resources involved
        @rtype:  ([], [])
        """

        actions = []
        resources = []

        for t in task.tags:
            if tag_utils.is_resource_tag(t):
                resource_type, resource_id = tag_utils.parse_resource_tag(t)
                resources.append('%s (%s)' % (resource_id, resource_type))
            else:
                tag_value = tag_utils.parse_value(t)
                actions.append(tag_value)

        return actions, resources

    def retrieve_tasks(self):
        """
        Override this with the specific call to the server to retrieve just
        the desired tasks.

        @return: response from the server
        """
        raise NotImplementedError()


class AllTasksSection(BaseTasksSection):
    FIELDS = ('tags', 'task_id', 'state', 'start_time', 'finish_time')

    def __init__(self, context, name, description):
        BaseTasksSection.__init__(self, context, name, description)

        self.list_command.add_option(self.all_flag)

        self.list_command.add_option(self.state_option)

    def retrieve_tasks(self, **kwargs):
        """
        :return:    list of pulp.bindings.responses.Task instances
        :rtype:     list
        """

        if kwargs.get(self.all_flag.keyword):
            tasks = self.context.server.tasks_search.search(fields=self.FIELDS)
        elif kwargs.get(self.state_option.keyword):
            states = kwargs[self.state_option.keyword]
            # This is a temorary fix(because of backward incompatible reasons)
            # until #1028 and #1041 are fixed.
            self.translate_state_discrepancy(states)
            tasks = self.context.server.tasks_search.search(
                filters={'state': {'$in': states}}, fields=self.FIELDS)
        else:
            tasks = self.context.server.tasks_search.search(
                filters={'state': {'$in': ['running', 'waiting']}}, fields=self.FIELDS)
        return tasks

    @staticmethod
    def translate_state_discrepancy(states):
        """
        Translates task state names that have discrepancy in cli and server mode.

        :param states: task state to parse
        :type states: list

        :return: translated task states
        :rtype: list
        """
        states_map = {'successful': 'finished', 'failed': 'error'}
        for state_name in states_map.keys():
            if state_name in states:
                del states[states.index(state_name)]
                states.append(states_map[state_name])

        return states


class RepoTasksSection(BaseTasksSection):
    def __init__(self, context, name, description):
        BaseTasksSection.__init__(self, context, name, description)

        self.list_command.create_option('--repo-id', _('identifies the repository to display'),
                                        required=True)

    def retrieve_tasks(self, **kwargs):
        """
        :return:    list of pulp.bindings.responses.Task instances
        :rtype:     list
        """
        repo_id = kwargs['repo-id']
        response = self.context.server.tasks.get_repo_tasks(repo_id)
        return response.response_body
