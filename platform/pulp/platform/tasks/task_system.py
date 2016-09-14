from celery import current_task


def get_current_task_id():
    """"
    Get the current task id from celery. If this is called outside of a running
    celery task it will return None

    :return: The ID of the currently running celery task or None if not in a task
    :rtype: str
    """
    if current_task and current_task.request and current_task.request.id:
        return current_task.request.id
    return None
