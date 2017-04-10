from pulp.server.managers import factory as managers


def bind(consumer_id, repo_id, distributor_id, binding_config):
    """
    Bind a repo to a consumer:
      1. Create the binding on the server.
    :param consumer_id: A consumer ID.
    :type consumer_id: str
    :param repo_id: A repository ID.
    :type repo_id: str
    :param distributor_id: A distributor ID.
    :type distributor_id: str
    :param binding_config: configuration options to use when generating the payload for this binding

    :returns Dictionary containing the result of the bind.
    :rtype: dict

    :raises pulp.server.exceptions.MissingResource: when given consumer does not exist
    """
    # Create the binding on the server
    bind_manager = managers.consumer_bind_manager()
    return bind_manager.bind(consumer_id, repo_id, distributor_id, binding_config)


def unbind(consumer_id, repo_id, distributor_id, options):
    """
    Unbind a  consumer.
    The itinerary is:
      1. Unbind the consumer from the repo on the server (mark the binding on the server as
         deleted.)
      2. Request that the consumer perform the unbind.
      3. Delete the binding on the server.

    :param consumer_id: A consumer ID.
    :type consumer_id: str
    :param repo_id: A repository ID.
    :type repo_id: str
    :param distributor_id: A distributor ID.
    :type distributor_id: str
    :param options: Unbind options passed to the handler.
    :type options: dict
    :returns Dictionary containing the result of the unbind.
    :rtype: dict
    """

    bind_manager = managers.consumer_bind_manager()
    binding = bind_manager.get_bind(consumer_id, repo_id, distributor_id)
    bind_manager.delete(consumer_id, repo_id, distributor_id, True)
    return binding


def force_unbind(consumer_id, repo_id, distributor_id, options):
    """
    Get the unbind itinerary.

    A forced unbind immediately deletes the binding instead
    of marking it deleted and going through that lifecycle.
    It is intended to be used to clean up orphaned bindings
    caused by failed/unconfirmed unbind actions on the consumer.

    The itinerary is:
      1. Delete the binding on the server.
      2. Request that the consumer perform the unbind.

    :param consumer_id: A consumer ID.
    :type consumer_id: str
    :param repo_id: A repository ID.
    :type repo_id: str
    :param distributor_id: A distributor ID.
    :type distributor_id: str
    :param options: Unbind options passed to the handler.
    :type options: dict
    """

    bind_manager = managers.consumer_bind_manager()
    bind_manager.delete(consumer_id, repo_id, distributor_id, True)

    response = TaskResult()

    if binding['notify_agent']:
        agent_manager = managers.consumer_agent_manager()
        task = agent_manager.unbind(consumer_id, repo_id, distributor_id, options)
        # we only want the task's ID, not the full task
        response.spawned_tasks.append({'task_id': task['task_id']})

    return response


@celery.task(base=Task, name='pulp.server.tasks.consumer.install_content')
def install_content(consumer_id, units, options, scheduled_call_id=None):
    """
    Install units on a consumer

    :param consumer_id: unique id of the consumer
    :type consumer_id: str
    :param units: units to install
    :type units: list or tuple
    :param options: options to pass to the install manager
    :type options: dict or None
    :param scheduled_call_id: id of scheduled call that dispatched this task
    :type scheduled_call_id: str
    :returns Dictionary representation of a task status
    :rtype: dictionary
    """
    agent_manager = managers.consumer_agent_manager()
    return agent_manager.install_content(consumer_id, units, options)


@celery.task(base=Task, name='pulp.server.tasks.consumer.update_content')
def update_content(consumer_id, units, options, scheduled_call_id=None):
    """
    Update units on a consumer.

    :param consumer_id: unique id of the consumer
    :type consumer_id: str
    :param units: units to install
    :type units: list or tuple
    :param options: options to pass to the install manager
    :type options: dict or None
    :param scheduled_call_id: id of scheduled call that dispatched this task
    :type scheduled_call_id: str
    :returns Dictionary representation of a task status
    :rtype: dictionary
    """
    agent_manager = managers.consumer_agent_manager()
    return agent_manager.update_content(consumer_id, units, options)


@celery.task(base=Task, name='pulp.server.tasks.consumer.uninstall_content')
def uninstall_content(consumer_id, units, options, scheduled_call_id=None):
    """
    Uninstall content from a consumer.

    :param consumer_id: unique id of the consumer
    :type consumer_id: str
    :param units: units to install
    :type units: list or tuple
    :param options: options to pass to the install manager
    :type options: dict or None
    :param scheduled_call_id: id of scheduled call that dispatched this task
    :type scheduled_call_id: str
    :returns Dictionary representation of a task status
    :rtype: dictionary
    """
    agent_manager = managers.consumer_agent_manager()
    return agent_manager.uninstall_content(consumer_id, units, options)

