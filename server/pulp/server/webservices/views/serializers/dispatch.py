from pulp.server.webservices.views.serializers.link import link_obj


def task_result_href(task):
    if task.get('task_id'):
        return {'_href': '/pulp/api/v2/tasks/%s/' % task['task_id']}
    return {}


def spawned_tasks(task):
    """
    For a given Task dictionary convert the spawned tasks list of ids to
    a list of link objects

    :param task: The dictionary representation of a task object in the database
    :type task: dict
    """
    spawned_tasks = []
    spawned = task.get('spawned_tasks')
    if spawned:
        for spawned_task_id in spawned:
            link = link_obj('/pulp/api/v2/tasks/%s/' % spawned_task_id)
            link['task_id'] = spawned_task_id
            spawned_tasks.append(link)
    return {'spawned_tasks': spawned_tasks}


def task_status(task):
    """
    Return serialized version of given TaskStatus document.

    :param task_status: Task status document object
    :type  task_status: pulp.server.db.model.TaskStatus

    :return: serialized task status
    :rtype:  dict
    """
    task_dict = {}
    attributes = ['task_id', 'worker_name', 'tags', 'state', 'error', 'spawned_tasks',
                  'progress_report', 'task_type', 'start_time', 'finish_time', 'result',
                  'exception', 'traceback', '_ns']
    for attribute in attributes:
        task_dict[attribute] = task[attribute]

    # This is to preserve backward compatibility for semantic versioning.
    task_dict['_id'] = task['id']
    task_dict['id'] = str(task['id'])

    return task_dict
