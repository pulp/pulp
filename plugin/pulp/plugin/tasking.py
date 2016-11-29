from pulp.app import models
from pulp.exceptions import exception_to_dict
from pulp.tasking.util import get_current_task_id


class Task(object):
    """
    The task which is currently executing.

    Attributes:
        id (str): The task identifier.

    """

    def __init__(self):
        self.id = get_current_task_id()

    def append_non_fatal_error(self, error):
        """
        Append and save a non-fatal error for the currently executing task.
        Fatal errors should not use this. Instead they should raise an Exception,
        preferably one that inherits from :class: `pulp.server.exception.PulpException`.

        This is saved in a structured way to the :attr: `~pulp.app.models.Task.non_fatal_errors`
        attribute on the :class: `~pulp.app.models.Task` model.

        Args:
            error (Exception): The non fatal error to be appended.

        Raises:
            pulp.app.models.Task.DoesNotExist: If not currently running inside a task.

        """
        task = models.Task.objects.get(id=self.id)
        serialized_error = exception_to_dict(error)
        task.non_fatal_errors.append(serialized_error)
        task.save()
