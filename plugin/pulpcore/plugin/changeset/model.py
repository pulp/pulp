import asyncio

from gettext import gettext as _
from logging import getLogger

from django.db import transaction
from django.db.models import Q
from django.db.utils import IntegrityError

from pulpcore.plugin.models import Artifact, ContentArtifact, RemoteArtifact
from pulpcore.plugin.download import BaseDownloader

log = getLogger(__name__)


class Pending:
    """
    Represents content related things contained within the remote repository.

    Attributes:
        _model (django.db.models.Model): A pending (wanted) model instance.
        _stored_model (django.db.models.Model): The model stored in the database.
        _settled (bool): All matters are settled and the object is ready
            to be (optionally created) and added to the repository.
    """

    __slots__ = (
        '_model',
        '_stored_model',
        '_settled'
    )

    @property
    def settled(self):
        """
        Check settled status.

        Returns:
            bool: All matters are settled.  See: _settled.
        """
        return self._settled

    def __init__(self, model):
        """
        Args:
            model (Model): A pending (wanted) model instance.
        """
        self._model = model
        self._stored_model = None
        self._settled = False

    def settle(self):
        """
        Ensures that all prerequisite matters have been settled and the
        pending object can be created in Pulp.
        """
        raise NotImplementedError()

    def save(self):
        """
        Save to the DB.
        """
        raise NotImplementedError()


class PendingContent(Pending):
    """
    Represents content that is contained within the remote repository.

    Attributes:
        model (pulpcore.plugin.models.Content): A content model instance.
        changeset (pulpcore.plugin.changeset.ChangeSet): A changeset.
            Set by the ContentIterator.
        artifacts (set): The set of related `PendingArtifact`.

    Examples:
        >>>
        >>> from pulpcore.plugin.models import Content
        >>>
        >>>
        >>> class Thing(Content):
        >>>    ...
        >>> thing = Thing()  # DB model instance.
        >>> ...
        >>> content = PendingContent(thing)
        >>>
    """

    __slots__ = (
        'changeset',
        'artifacts',
    )

    def __init__(self, model, artifacts=()):
        """
        Args:
            model (pulpcore.plugin.models.Content): A content model instance.
                This instance will be used to store newly created content in the DB.
            artifacts (iterable): A set of PendingArtifact.
        """
        super().__init__(model)
        self.artifacts = set(artifacts)
        self.changeset = None

    @property
    def key(self):
        """
        The natural key as a dictionary.

        Returns:
            dict: The natural key.
        """
        return {f: getattr(self._model, f) for f in self._model.natural_key_fields()}

    def bind(self, changeset):
        """
        Bind to a changeset.
        Creates an association to a changeset being applied.

        Args:
            changeset (pulpcore.plugin.changeset.ChangeSet): A changeset.

        Returns:
            PendingContent: self to support comprehensions.
        """
        self.changeset = changeset
        return self

    @property
    def model(self):
        """
        The model attribute getter.

        Returns:
            pulpcore.plugin.models.Content: The pending model.
        """
        return self._model

    @property
    def stored_model(self):
        """
        The stored model attribute getter.

        Returns:
            pulpcore.plugin.models.Content: The stored model.
        """
        return self._stored_model

    @stored_model.setter
    def stored_model(self, model):
        """
        The stored model attribute getter.

        Notes:

          - The artifacts are matched by `relative_path` and their
            their stored_model set.

        Args:
            model (pulpcore.plugin.models.Content): The stored model.
        """
        self._stored_model = model
        artifacts = {a.relative_path: a for a in self.artifacts}
        self.artifacts.clear()
        for content_artifact in model.contentartifact_set.all():
            try:
                artifact = artifacts[content_artifact.relative_path]
                if not artifact.model.is_equal(content_artifact.artifact):
                    continue
                artifact.stored_model = content_artifact.artifact
                self.artifacts.add(artifact)
            except KeyError:
                log.error(_('Artifact not matched.'))

    def settle(self):
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
        self.save()
        self._settled = True

    def save(self):
        """
        Save the content and related artifacts in a single DB transaction.
        Due to race conditions, the content may already exist raising an IntegrityError.
        When this happens, the model is fetched and _stored_model is updated.
        """
        with transaction.atomic():
            if not self._stored_model:
                try:
                    with transaction.atomic():
                        self._model.save()
                except IntegrityError:
                    model = type(self._model).objects.get(**self.key)
                    self._stored_model = model
                else:
                    self._stored_model = self._model

            for artifact in self.artifacts:
                artifact.save()


class PendingArtifact(Pending):
    """
    Represents an artifact related to content that is contained within
    the remote repository.

    Attributes:
        url (str): The URL used to download the artifact.
        relative_path (str): The relative path within the content.
        content (PendingContent): The associated pending content.
            This is the reverse relationship.

    Examples:
        >>>
        >>> from pulpcore.plugin.models import Artifact
        >>>
        >>> model = Artifact(...)  # DB model instance.
        >>> download = ...
        >>> ...
        >>> artifact = PendingArtifact(model, 'http://zoo.org/lion.rpm', 'lion.rpm')
        >>>
    """

    __slots__ = (
        'url',
        'relative_path',
        'content',
    )

    def __init__(self, model, url, relative_path, content=None):
        """
        Args:
            model (pulpcore.plugin.models.Artifact): A pending artifact model.
            url (str): The URL used to download the artifact.
            relative_path (str): The relative path within the content.
            content (PendingContent): The associated pending content.
                This is the reverse relationship.
        """
        super().__init__(model)
        self.url = url
        self.relative_path = relative_path
        self.content = content
        if content:
            content.artifacts.add(self)

    @property
    def model(self):
        """
        The model getter.

        Returns:
            pulpcore.plugin.models.Artifact: The pending model.
        """
        return self._model

    @property
    def stored_model(self):
        """
        The stored model getter.

        Returns:
            pulpcore.plugin.models.Artifact: The stored model.
        """
        return self._stored_model

    @stored_model.setter
    def stored_model(self, model):
        """
        The stored model setter.

        Args:
            model (pulpcore.plugin.models.Artifact): The stored model.
        """
        self._stored_model = model

    @property
    def changeset(self):
        """
        The changeset getter.

        Returns:
            pulpcore.plugin.changeset.Changeset: The active changeset.
        """
        return self.content.changeset

    @property
    def importer(self):
        """
        The importer getter.

        Returns:
            pulpcore.plugin.models.Importer: An importer.
        """
        return self.changeset.importer

    @property
    def downloader(self):
        """
        A downloader used to download the artifact.
        The downloader may be a NopDownloader (no-operation) when:
        - The _stored_model is set to an model fetched from the DB.
        - The download policy is deferred.

        Returns:
            asyncio.Future: A download future based on a downloader.
        """
        def done(task):
            try:
                task.result()
            except Exception:
                pass
            else:
                self.downloaded(downloader)
        if self.importer.is_deferred or self._stored_model:
            downloader = NopDownloader()
            future = asyncio.ensure_future(downloader.run())
        else:
            downloader = self.importer.get_downloader(self.url)
            future = asyncio.ensure_future(downloader.run())
            future.add_done_callback(done)
        return future

    def downloaded(self, downloader):
        """
        The artifact (file) has been downloaded.
        A new _stored_model is created (and assigned) for the downloaded file.

        Args:
            downloader (BaseDownloader): The downloader that successfully completed.
        """
        self._stored_model = Artifact(file=downloader.path, **downloader.artifact_attributes)

    def artifact_q(self):
        """
        Get a query for the actual artifact.

        Returns:
            django.db.models.Q: A query to get the actual artifact.
        """
        q = Q(pk=None)
        for field in Artifact.RELIABLE_DIGEST_FIELDS:
            digest = getattr(self._model, field)
            if digest:
                q |= Q(**{field: digest})
        return q

    def settle(self):
        """
        Ensures that all prerequisite matters pertaining to adding the artifact
        to the DB have been settled:

        Notes:
            Called whenever an artifact has been processed.
        """
        self._settled = True

    def save(self):
        """
        Update the DB:
         - Create (or fetch) the Artifact.
         - Create (or fetch) the ContentArtifact.
         - Create (or update) the RemoteArtifact.
        """
        if self._stored_model:
            try:
                with transaction.atomic():
                    self._stored_model.save()
            except IntegrityError:
                q = self.artifact_q()
                self._stored_model = Artifact.objects.get(q)

        try:
            with transaction.atomic():
                content_artifact = ContentArtifact(
                    relative_path=self.relative_path,
                    content=self.content.stored_model,
                    artifact=self._stored_model)
                content_artifact.save()
        except IntegrityError:
            content_artifact = ContentArtifact.objects.get(
                relative_path=self.relative_path,
                content=self.content.stored_model)
            if self._stored_model:
                content_artifact.artifact = self._stored_model
                content_artifact.save()

        digests = {f: getattr(self._model, f) for f in Artifact.DIGEST_FIELDS}

        try:
            with transaction.atomic():
                remote_artifact = RemoteArtifact(
                    url=self.url,
                    importer=self.importer,
                    content_artifact=content_artifact,
                    size=self._model.size,
                    **digests)
                remote_artifact.save()
        except IntegrityError:
            q_set = RemoteArtifact.objects.filter(
                importer=self.importer,
                content_artifact=content_artifact)
            q_set.update(
                url=self.url,
                size=self._model.size,
                **digests)

    def __hash__(self):
        return hash(self.relative_path)


class NopDownloader(BaseDownloader):
    """
    A no-operation (NOP) downloader.
    """

    def __init__(self):
        super().__init__('')

    async def run(self):
        pass


class NopPendingArtifact(PendingArtifact):
    """
    No operation (NOP) pending artifact.
    """

    def __init__(self, content):
        """
        Args:
            content (PendingContent): The associated pending content.
        """
        super().__init__(Artifact(), '', '')
        self.content = content

    @property
    def downloader(self):
        return asyncio.ensure_future(NopDownloader().run())

    def downloaded(self, downloader):
        pass

    def settle(self):
        pass

    def save(self):
        pass
