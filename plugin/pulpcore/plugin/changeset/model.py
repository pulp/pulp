from gettext import gettext as _
from logging import getLogger

from django.db.models import Q
from django.db.utils import IntegrityError
from django.db import transaction
from django.core.files import File

from pulpcore.app.models import Artifact, ContentArtifact, DeferredArtifact
from pulpcore.download import Event
from pulpcore.plugin.download.monitor import DownloadMonitor


log = getLogger(__name__)


class Pending:
    """
    Represents content related things contained within the remote repository.

    Attributes:
        model (Model): A pending (wanted) model instance.
        settled (bool): All matters are settled and the object is ready
            to be (optionally created) and added to the repository.
        fetched (bool): model has been fetched from the DB.
    """

    __slots__ = (
        'model',
        'settled',
        'fetched',
    )

    def __init__(self, model):
        """
        Args:
            model (Model): A pending (wanted) model instance.
        """
        self.model = model
        self.settled = False
        self.fetched = False

    def settle(self):
        """
        Ensures that all prerequisite matters have been settled and the
        pending object can be created in Pulp.
        """
        raise NotImplementedError()

    def update(self, model):
        """
        Update with a fetched model instance.
        Args:
            model (pulpcore.app.models.Model): The fetched model.
        """
        self.model = model
        self.fetched = True

    def save(self):
        """
        Save to the DB.
        """
        raise NotImplementedError()


class PendingContent(Pending):
    """
    Represents content that is contained within the remote repository.

    Attributes:
        model (pulpcore.plugin.Content): A content model instance.
        changeset (pulpcore.plugin.ChangeSet): A changeset.
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
        return {f.name: getattr(self.model, f.name) for f in self.model.natural_key_fields}

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

    def update(self, model):
        """
        Update this `model` stored with the specified model that has been
        fetched from the database. The artifacts are matched by `relative_path`
        and their model object is replaced by the fetched model.

        Args:
            model (pulpcore.plugin.Content): A fetched content model object.
        """
        super().update(model)
        artifacts = {a.relative_path: a for a in self.artifacts}
        self.artifacts.clear()
        for content_artifact in model.contentartifact_set.all():
            try:
                matched = artifacts[content_artifact.relative_path]
                if not matched.model.is_equal(content_artifact.artifact):
                    continue
                matched.update(content_artifact.artifact)
                self.artifacts.add(matched)
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
        self.settled = True

    def save(self):
        """
        Save the content and related artifacts in a single DB transaction.
        Due to race conditions, the content may already exist raising an IntegrityError.
        When this happens, the model is fetched and replaced.
        """
        with transaction.atomic():
            try:
                with transaction.atomic():
                    self.model.save()
            except IntegrityError:
                content = type(self.model).objects.get(**self.key)
                self.update(content)

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
        monitor (pulpcore.plugin.DownloadMonitor): Used to collect information about
            downloaded artifacts.
        _path (str): An absolute path to a downloaded artifact.

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
        'monitor',
        'content',
        '_path',
    )

    def __init__(self, model, url, relative_path):
        """
        Args:
            model (pulpcore.plugin.models.Artifact): A pending artifact model instance.
                This instance will be used to store a newly created or updated
                pending artifact in the DB.
            url (str): The URL used to download the artifact.
            relative_path (str): The relative path within the content.
        """
        super().__init__(model)
        self.url = url
        self.relative_path = relative_path
        self.monitor = None
        self.content = None
        self._path = ''

    @property
    def changeset(self):
        """
        Returns:
            pulpcore.plugin.changeset.Changeset: The active changeset.
        """
        return self.content.changeset

    @property
    def importer(self):
        """
        Returns:
            pulpcore.plugin.models.Importer: An importer.
        """
        return self.changeset.importer

    def downloader(self):
        """
        Get a downloader.

        Returns:
            pulpcore.download.Download: A downloader.
        """
        def succeeded(event):
            self._path = event.download.writer.path
        download = self.importer.get_download(
            self.url,
            self.relative_path,
            self.model)
        download.attachment = self
        download.register(Event.SUCCEEDED, succeeded)
        self.monitor = DownloadMonitor(download)
        return download

    def artifact_q(self):
        """
        Get a query for the actual artifact.

        Returns:
            django.db.models.Q: A query to get the actual artifact.
        """
        q = Q()
        for field in Artifact.RELIABLE_DIGEST_FIELDS:
            digest = getattr(self.model, field)
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
        self.settled = True

    def save(self):
        """
        Update the DB model to store the downloaded file.
        Then, save in the DB.
        """
        artifact = None

        if not self.fetched:
            if self._path:  # downloaded
                try:
                    with transaction.atomic():
                        self.model = Artifact(
                            file=File(open(self._path, mode='rb')),
                            **self.monitor.dict())
                        self.model.save()
                except IntegrityError:
                    q = self.artifact_q()
                    self.model = Artifact.objects.get(q)
                finally:
                    artifact = self.model
        else:
            artifact = self.model

        try:
            with transaction.atomic():
                content_artifact = ContentArtifact(
                    relative_path=self.relative_path,
                    content=self.content.model,
                    artifact=artifact)
                content_artifact.save()
        except IntegrityError:
            content_artifact = ContentArtifact.objects.get(
                relative_path=self.relative_path,
                content=self.content.model)
            if self.fetched:
                content_artifact.artifact = artifact
                content_artifact.save()

        digests = {f: getattr(self.model, f) for f in Artifact.DIGEST_FIELDS}

        try:
            with transaction.atomic():
                deferred_artifact = DeferredArtifact(
                    url=self.url,
                    importer=self.importer,
                    content_artifact=content_artifact,
                    size=self.model.size,
                    **digests)
                deferred_artifact.save()
        except IntegrityError:
            q_set = DeferredArtifact.objects.filter(
                importer=self.importer,
                content_artifact=content_artifact)
            q_set.update(
                url=self.url,
                size=self.model.size,
                **digests)

    def __hash__(self):
        return hash(self.relative_path)
