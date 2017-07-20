from gettext import gettext as _
from logging import getLogger
import hashlib

from django.db.utils import IntegrityError
from django.db import transaction
from django.core.files import File
from django.http import QueryDict

from pulpcore.app.apps import get_plugin_config
from pulpcore.app.models import Artifact, ContentArtifact

log = getLogger(__name__)


class Remote:
    """
    Represents content related things contained within the remote repository.

    Attributes:
        model (Model): A remote (wanted) model instance.
        settled (bool): All matters are settled and the object is ready
            to be (optionally created) and added to the repository.
    """

    __slots__ = (
        'model',
        'settled'
    )

    def __init__(self, model):
        """
        Args:
            model (Model): A remote (wanted) model instance.
        """
        self.model = model
        self.settled = False

    def save(self):
        """
        Save the model.
        """
        self.model.save()


class RemoteContent(Remote):
    """
    Represents content that is contained within the remote repository.

    Attributes:
        model (pulpcore.plugin.Content): A content model instance.
        artifacts (set): The set of related `RemoteArtifact`.

    Examples:
        >>>
        >>> from pulpcore.plugin.models import Content
        >>>
        >>>
        >>> class Thing(Content):
        >>>    ...
        >>> thing = Thing()  # DB model instance.
        >>> ...
        >>> content = RemoteContent(thing)
        >>>
    """

    __slots__ = ('artifacts',)

    def __init__(self, model):
        """
        Args:
            model (pulpcore.plugin.models.Content): A content model instance.
                This instance will be used to store newly created content in the DB.
        """
        super(RemoteContent, self).__init__(model)
        self.artifacts = set()

    @property
    def key(self):
        """
        The natural key as a dictionary.

        Returns:
            dict: The natural key.
        """
        return {f.name: getattr(self.model, f.name) for f in self.model.natural_key_fields}

    def update(self, model):
        """
        Update this `model` stored with the specified model that has been
        fetched from the database. The artifacts are matched by `relative_path`
        and their model object is replaced by the fetched model.

        Args:
            model (pulpcore.plugin.Content): A fetched content model object.
        """
        self.model = model
        known = {a.content_artifact.relative_path: a for a in self.artifacts}
        self.artifacts.clear()
        for content_artifact in ContentArtifact.objects.filter(content=model):
            try:
                found = known[content_artifact.relative_path]
                found.content_artifact = content_artifact
                self.artifacts.add(found)
            except KeyError:
                log.error(_('Artifact not matched.'))

    def settle(self, deferred=False):
        """
        Ensures that all prerequisite matters pertaining to adding the content
        to a repository have been settled:
        - All artifacts are settled.
        - Content created.
        - Artifacts created.

        Notes:
            Called whenever an artifact has been downloaded.
        """
        for artifact in self.artifacts:
            if not artifact.settled:
                return
        self.save(deferred=deferred)
        self.settled = True

    def save(self, deferred=False):
        """
        Save the content and related artifacts in a single DB transaction.
        Due to race conditions, the content may already exist raising an IntegrityError.
        When this happens, the model is fetched and replaced.
        """
        is_duplicate = False
        with transaction.atomic():
            try:
                super(RemoteContent, self).save()
            except IntegrityError:
                is_duplicate = True
            else:

                for remote_artifact in self.artifacts:
                    if not remote_artifact.content_artifact.artifact_id:
                        if not deferred:
                            artifact = self.validate_and_create_artifact(remote_artifact.model,
                                                                         remote_artifact.download)
                            remote_artifact.content_artifact.artifact = artifact
                        remote_artifact.model.save()
                        remote_artifact.content_artifact.save()

    def validate_and_create_artifact(self, remote_artifact, download):
        """
        Create an Artifact from a RemoteArtifact and a downloaded file

        Args:
            remote_artifact (pulpcore.plugin.RemoteArtifact): remote artifact
            download (download object): download
            :return:
        """
        file = File(open(download.writer.path, mode='rb'))
        file.hashers = download.writer.hashers

        # Build data from RemoteArtifact
        data = QueryDict('', mutable=True)
        data['file'] = file
        if remote_artifact.size:
            data['size'] = remote_artifact.size
        for hasher in hashlib.algorithms_guaranteed:
            if getattr(remote_artifact, hasher, None):
                data[hasher] = getattr(remote_artifact, hasher, None)

        serializer_class = get_plugin_config("pulp_app").named_serializers["ArtifactSerializer"]
        serializer = serializer_class(data=data)
        serializer.validate(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.save()


class RemoteArtifact(Remote):
    """
    Represents an artifact related to content that is contained within
    the remote repository.

    Attributes:
        download (pulpcore.download.Download): An object used to download the content.
        content_artifact (ContentArtifact): The association between an Artifact and Content.
        path (str): Absolute path to the downloaded file.  May be (None) when
            downloading is deferred or the artifact has already been downloaded.

    Examples:
        >>>
        >>> from pulpcore.plugin.models import ContentArtifact, DeferredArtifact
        >>>
        >>> model = DeferredArtifact(...)
        >>> content_artifact = ContentArtifact(...)
        >>> download = ...
        >>> ...
        >>> artifact = RemoteArtifact(model, content_artifact, download)
        >>>
    """

    __slots__ = (
        'content',
        'content_artifact',
        'download',
        'path'
    )

    def __init__(self, model, content_artifact, download):
        """

        Args:
            model (pulpcore.plugin.models.DeferredArtifact): A remote artifact model instance.
                This object will be used to determine if an Artifact exists or one needs to
                created.
            download (pulpcore.download.Download): A An object used to download the content.
        """
        super(RemoteArtifact, self).__init__(model)
        self.content_artifact = content_artifact
        self.download = download
        self.download.attachment = self
        # NopDownload doesn't have a writer
        if download.writer:
            self.path = download.writer.path
        else:
            self.path = None

    def settle(self):
        """
        Ensures that all prerequisite matters pertaining to adding the artifact
        to the DB have been settled:

        Notes:
            Called whenever an artifact has been processed.
        """
        self.settled = True

    def save(self):
        """
        Update the DB model to store the downloaded file.
        Then, save in the DB.
        """
        super(RemoteArtifact, self).save()

    def __hash__(self):
        return hash(self.model.id)
