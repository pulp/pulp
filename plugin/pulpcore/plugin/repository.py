from contextlib import suppress
from gettext import gettext as _
from django.db import transaction
from django.db.utils import IntegrityError


from pulpcore.app import models
from pulpcore.tasking.util import get_current_task_id
from pulpcore.exceptions import ResourceImmutableError


class RepositoryVersion:
    """
    A context manager used to manage RepositoryVersions

    Examples:
        >>>
        >>> with RepositoryVersion.create(repository) as new_version:
        >>>     new_version.add_content(content)
        >>>     new_version.remove_content(content)
        >>>     changeset = ChangeSet(importer, new_version, additions=additions,
        >>>                      removals=removals)
        >>>
        >>> latest_version = RepositoryVersion.latest(repository)
        >>> content = latest_version.content
    """

    @classmethod
    def latest(cls, repository):
        """
        Get the latest RepositoryVersion on a repository

        Args:
            repository (pulpcore.plugin.repository): to get the latest version of

        Returns:
            pulpcore.plugin.repository.RepositoryVersion: The latest RepositoryVersion

        """
        with suppress(models.RepositoryVersion.DoesNotExist):

            model = repository.versions.exclude(complete=False).latest()
            return RepositoryVersion(model)

    @classmethod
    def create(cls, repository):
        """
        Create a new RepositoryVersion

        Args:
            repository (pulpcore.plugin.repository): to create a new version of

        Returns:
            pulpcore.plugin.repository.RepositoryVersion: The Created RepositoryVersion
        """

        assert get_current_task_id() is not None, _('RepositoryVersion creation must be run inside '
                                                    'a task')

        with transaction.atomic():
            version = models.RepositoryVersion(
                repository=repository,
                number=repository.last_version + 1)
            repository.last_version = version.number
            repository.save()
            version.save()
            resource = models.CreatedResource(content_object=version)
            resource.save()
            return cls(version, resource)

    def __init__(self, model, resource=None):
        """
        Args:
            model (pulpcore.models.repository.RepositoryVersion)
            resource (pulpcore.models.task.CreatedResource)
        """
        self._model = model
        self._created_resource = resource

    @property
    def number(self):
        return self._model.number

    @property
    def content(self):
        """
        QuerySet of content on this repository version

        Returns:
            QuerySet: The Content objects that are related to this version.
        """
        return self._model.content

    def add_content(self, content):
        """
        Add a content unit to the repository.

        Args:
           content (pulpcore.plugin.models.Content): a content model to add

        Raise:
            pulpcore.exception.ResourceImmutableError: if add_content is called on a
                complete RepositoryVersion
        """
        if self._model.complete:
            raise ResourceImmutableError(self._model)
        with suppress(IntegrityError):
            association = models.RepositoryContent(
                repository=self._model.repository,
                content=content,
                version_added=self._model)
            association.save()

    def remove_content(self, content):
        """
        Remove content from the repository.

        Args:
            content (pulpcore.plugin.models.Content): A content model to remove

        Raise:
            pulpcore.exception.ResourceImmutableError: if remove_content is called on a
                complete RepositoryVersion
        """

        if self._model.complete:
            raise ResourceImmutableError(self._model)

        q_set = models.RepositoryContent.objects.filter(
            repository=self._model.repository,
            content=content,
            version_removed=None)
        q_set.update(version_removed=self._model)

    def complete(self):
        """
        Save the repository version when all operations are done on it
        """
        self._model.complete = True
        self._model.save()

    def delete(self):
        """
        Deletes an incomplete Repository Version

        This method deletes a RepositoryVersion only if its 'complete' property is False. All
        RepositoryContent added in the deleted RepositoryVersion are deleted also. All
        RepositoryContent removed in the deleted RepositoryVersion has the version_removed set to
        None.

        Raise:
            pulpcore.exception.ResourceImmutableError: if delete() is called on a complete
                RepositoryVersion
        """
        if self._model.complete:
            raise ResourceImmutableError(self._model)
        with transaction.atomic():
            models.RepositoryContent.objects.filter(version_added=self._model).delete()
            models.RepositoryContent.objects.filter(version_removed=self._model)\
                .update(version_removed=None)
            self._model.repository.last_version = self._model.number - 1
            self._model.repository.save()
            self._model.delete()
            if self._created_resource is not None:
                self._created_resource.delete()

    def __enter__(self):
        """
        Create the repository version

        Returns:
            RepositoryVersion: self
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Save the RepositoryVersion if no errors are raised, delete it if not
        """
        if exc_value:
            self.delete()
        else:
            self.complete()
