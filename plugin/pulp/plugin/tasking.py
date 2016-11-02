from pulp.app.models import Task
from pulp.tasking import get_current_task_id


class TaskController(object):
    """
    An interface to the currently running task.

    With this object you can record non-fatal exceptions as they occur.

    This object is natively task aware. When called inside of a task it will append the non-fatal
    exception to the currently running task. When called outside of a task a
    :class: `pulp.app.models.Task.DoesNotExist` Exception is raised.

    Fatal errors should not use this. Instead they should raise an Exception, preferably one that
    inherits from :class: `pulp.server.exception.PulpException`.
    """

    @classmethod
    def append_non_fatal_error(cls, error):
        """
        Append and save a non-fatal error for the currently executing task.

        This is saved in a structured way to the :attr: `~pulp.app.models.Task.non_fatal_errors`
        attribute on the :class: `~pulp.app.models.Task` model.

        :param error: The non fatal error to be appended.
        :type error: dict

        :raises :class: `pulp.app.models.Task.DoesNotExist`: If not currently running inside a
                                                             task.
        """
        task_id = get_current_task_id()
        task_obj = Task.objects.get(id=task_id)
        if not isinstance(task_obj.non_fatal_errors, list):
            task_obj.non_fatal_errors = [error]
        else:
            task_obj.non_fata_errors.append(error)
        task_obj.save()
