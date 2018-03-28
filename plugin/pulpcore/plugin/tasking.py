from rq.job import get_current_job

from pulpcore.app import models
from pulpcore.exceptions import exception_to_dict

# Support plugins dispatching tasks
from pulpcore.tasking.tasks import enqueue_with_reservation  # noqa

# Support plugins working with the working directory.
from pulpcore.tasking.services.storage import WorkingDirectory  # noqa


class Task:
    """
    The task which is currently executing.

    Attributes:
        job (str): The RQ job associated with the task.
    """

    def __init__(self):

        self.job = get_current_job()

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
        task = models.Task.objects.get(id=self.job.id)
        serialized_error = exception_to_dict(error)
        task.non_fatal_errors.append(serialized_error)
        task.save()
