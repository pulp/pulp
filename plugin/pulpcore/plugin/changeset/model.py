from gettext import gettext as _
from logging import getLogger

from django.db.utils import IntegrityError
from django.db import transaction
from django.core.files import File


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
        known = {a.model.relative_path: a for a in self.artifacts}
        self.artifacts.clear()
        for artifact in model.artifacts.all():
            try:
                found = known[artifact.relative_path]
                found.model = artifact
                self.artifacts.add(found)
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
        is_duplicate = False
        with transaction.atomic():
            try:
                super(RemoteContent, self).save()
            except IntegrityError:
                is_duplicate = True
            else:
                for artifact in self.artifacts:
                    artifact.model.content = self.model
                    artifact.save()
        if is_duplicate:
            model = type(self.model)
            content = model.objects.get(**self.key)
            self.update(content)


class RemoteArtifact(Remote):
    """
    Represents an artifact related to content that is contained within
    the remote repository.

    Attributes:
        download (pulpcore.download.Download): An object used to download the content.
        content (RemoteContent): The associated remote content.
        path (str): Absolute path to the downloaded file.  May be (None) when
            downloading is deferred or the artifact has already been downloaded.

    Examples:
        >>>
        >>> from pulpcore.plugin.models import Artifact
        >>>
        >>> model = Artifact(...)  # DB model instance.
        >>> download = ...
        >>> ...
        >>> artifact = RemoteArtifact(model, download)
        >>>
    """

    __slots__ = (
        'content',
        'download',
        'path'
    )

    def __init__(self, model, download):
        """

        Args:
            model (pulpcore.plugin.models.Artifact): An artifact model instance.
                This instance will be used to store a newly created or updated
                artifact in the DB.
            download (pulpcore.download.Download): A An object used to download the content.
        """
        super(RemoteArtifact, self).__init__(model)
        self.download = download
        self.download.attachment = self
        self.path = download.writer.path
        self.content = None

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
        if self.path:
            self.model.file = File(open(self.path, mode='rb'))
            self.model.downloaded = True
        super(RemoteArtifact, self).save()

    def __hash__(self):
        return hash(self.model.id)
