from gettext import gettext as _
from logging import getLogger

from celery import shared_task
from django.db import transaction

from pulpcore.app import models
from pulpcore.app import serializers
from pulpcore.tasking.tasks import UserFacingTask


log = getLogger(__name__)


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


@shared_task(base=UserFacingTask)
def delete_version(pk):
    """
    Delete a repository version by squashing its changes with the next newer version. This ensures
    that the content set for each version stays the same.

    There must be a newer version to squash into. If we deleted the latest version, the next content
    change would create a new one of the same number, which would violate the immutability
    guarantee.

    Args:
        pk (UUID): the primary key for a RepositoryVersion to delete

    Raises:
        models.RepositoryVersion.DoesNotExist: if there is not a newer version to squash into.
            TODO: something more friendly
    """
    with transaction.atomic():
        try:
            version = models.RepositoryVersion.objects.get(pk=pk)
        except models.RepositoryVersion.DoesNotExist:
            log.info(_('The repository version was not found. Nothing to do.'))
            return

        log.info(_('Deleting and squashing version %(v)d of repository %(r)s'),
                 {'v': version.number, 'r': version.repository.name})

        repo_relations = models.RepositoryContent.objects.filter(repository=version.repository)

        try:
            next_version = version.next()
        except models.RepositoryVersion.DoesNotExist:
            # version is the latest version so simply update repo contents and delete the version
            repo_relations.filter(version_added=version).delete()
            repo_relations.filter(version_removed=version).update(version_removed=None)
            version.delete()
            return

        # delete any relationships added in the version being deleted and removed in the next one.
        repo_relations.filter(version_added=version, version_removed=next_version).delete()

        # If the same content is deleted in version, but added back in next_version
        # set version_removed field in relation to None, and remove relation adding the content
        # in next_version
        content_added = repo_relations.filter(version_added=next_version).values_list('content_id')

        # use list() to force the evaluation of the queryset, otherwise queryset is affected
        # by the update() operation before delete() is ran
        content_removed_and_readded = list(repo_relations.filter(version_removed=version,
                                                                 content_id__in=content_added)
                                           .values_list('content_id'))

        repo_relations.filter(version_removed=version,
                              content_id__in=content_removed_and_readded)\
            .update(version_removed=None)

        repo_relations.filter(version_added=next_version,
                              content_id__in=content_removed_and_readded)\
            .delete()

        # "squash" by moving other additions and removals forward to the next version
        repo_relations.filter(version_added=version).update(version_added=next_version)
        repo_relations.filter(version_removed=version).update(version_removed=next_version)

        # With no more relationships remaining, delete the version.
        version.delete()
