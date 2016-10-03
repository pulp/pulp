from pulp.server.async.tasks import TaskResult
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

    :returns TaskResult containing the result of the bind & any spawned tasks or a dictionary
             of the bind result if no tasks were spawned.
    :rtype: TaskResult

    :raises pulp.server.exceptions.MissingResource: when given consumer does not exist
    """
    # Create the binding on the server
    bind_manager = managers.consumer_bind_manager()
    binding = bind_manager.bind(consumer_id, repo_id, distributor_id, binding_config)

    response = TaskResult(result=binding)

    return response


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
    :returns TaskResult containing the result of the unbind & any spawned tasks or a dictionary
             of the unbind result if no tasks were spawned.
    :rtype: TaskResult
    """

    bind_manager = managers.consumer_bind_manager()
    binding = bind_manager.get_bind(consumer_id, repo_id, distributor_id)

    response = TaskResult(result=binding)

    bind_manager.delete(consumer_id, repo_id, distributor_id, True)

    return response


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
    :returns TaskResult containing the result of the unbind & any spawned tasks or a dictionary
             of the unbind result if no tasks were spawned.
    :rtype: TaskResult
    """

    bind_manager = managers.consumer_bind_manager()
    bind_manager.delete(consumer_id, repo_id, distributor_id, True)

    response = TaskResult()

    return response
