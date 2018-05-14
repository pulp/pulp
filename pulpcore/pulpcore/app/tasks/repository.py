from gettext import gettext as _
from logging import getLogger

from django.db import transaction

from pulpcore.app import models
from pulpcore.app import serializers

log = getLogger(__name__)


def delete(repo_id):
    """
    Delete a :class:`~pulpcore.app.models.Repository`

    Args:
        repo_id (UUID): The name of the repository to be deleted
    """

    models.Repository.objects.filter(pk=repo_id).delete()


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

        version.delete()


def add_and_remove(repository_pk, add_content_units, remove_content_units):
    """
    Create a new repository version by adding and then removing content units.

    Args:
        repository_pk (UUID): The primary key for a Repository for which a new Repository Version
            should be created.
        add_content_units (list): List of PKs for :class:`~pulpcore.app.models.Content` that
            should be added to the previous Repository Version for this Repository.
        remove_content_units (list): List of PKs for:class:`~pulpcore.app.models.Content` that
            should be removed from the previous Repository Version for this Repository.
    """
    repository = models.Repository.objects.get(pk=repository_pk)

    with models.RepositoryVersion.create(repository) as new_version:
        for pk in add_content_units:
            content = models.Content.objects.get(pk=pk)
            new_version.add_content(content)
        for pk in remove_content_units:
            content = models.Content.objects.get(pk=pk)
            new_version.remove_content(content)
