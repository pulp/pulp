from celery import shared_task

from pulpcore.app import models
from pulpcore.app import serializers
from pulpcore.tasking.tasks import UserFacingTask


@shared_task(base=UserFacingTask)
def delete(repo_id):
    """
    Delete a :class:`~pulpcore.app.models.Repository`

    Args:
        repo_id (UUID): The name of the repository to be deleted
    """

    models.Repository.objects.filter(pk=repo_id).delete()


@shared_task(base=UserFacingTask)
def update(repo_id, partial=True, data=None):
    """
    Updates a :class:`~pulpcore.app.models.Repository`

    Args:
        repo_id (UUID): The id of the repository to be updated
        partial (bool): Boolean to allow partial updates. If set to False, values for all
                        required fields must be passed or a validation error will be raised.
                        Defaults to True
        data (QueryDict): dict of attributes to change and their new values; if None, no attempt to
                     update the repository object will be made
    """
    instance = models.Repository.objects.get(pk=repo_id)
    serializer = serializers.RepositorySerializer(instance, data=data, partial=partial)
    serializer.is_valid(raise_exception=True)
    serializer.save()
