from pulpcore.app import models
from pulpcore.exceptions import exception_to_dict
from pulpcore.tasking.util import get_current_task_id

# Support plugins creating Celery tasks.
from pulpcore.tasking.tasks import UserFacingTask  # noqa

# Support plugins working with the working directory.
from pulpcore.tasking.services.storage import WorkingDirectory  # noqa


class Task:
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
        preferably one that inherits from :class: `pulpcore.server.exception.PulpException`.

        This is saved in a structured way to the :attr: `~pulpcore.app.models.Task.non_fatal_errors`
        attribute on the :class: `~pulpcore.app.models.Task` model.

        Args:
            error (Exception): The non fatal error to be appended.

        Raises:
            pulpcore.app.models.Task.DoesNotExist: If not currently running inside a task.

        """
        task = models.Task.objects.get(id=self.id)
        serialized_error = exception_to_dict(error)
        task.non_fatal_errors.append(serialized_error)
        task.save()
