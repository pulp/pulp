from gettext import gettext as _


class DeclarativeArtifact:
    """
    Relates an Artifact, how to download it, and its relative_path for publishing.

    This is used by the Stages API stages to determine if an Artifact is already present and ensure
    Pulp can download it in the future. The `artifact` can be either saved or unsaved. If unsaved,
    the `artifact` attributes may be incomplete because not all digest information can be computed
    until the Artifact is downloaded.

    Attributes:
        artifact - An Artifact either saved or unsaved. If unsaved, it may have partial digest
            information attached to it.
        url - the url to fetch the Artifact from.
        relative_path - the relative_path this Artifact should be published at for any Publication.
        remote - The remote used to fetch this Artifact.

    Raises:
        ValueError: If `artifact`, `url`, `relative_path`, or `remote` are not specified.
    """

    __slots__ = ('artifact', 'url', 'relative_path', 'remote')

    def __init__(self, artifact=None, url=None, relative_path=None, remote=None):
        if not url:
            raise ValueError(_("DeclarativeArtifact must have a 'url'"))
        if not relative_path:
            raise ValueError(_("DeclarativeArtifact must have a 'relative_path'"))
        if not remote:
            raise ValueError(_("DeclarativeArtifact must have a 'remote'"))
        if not artifact:
            raise ValueError(_("DeclarativeArtifact must have a 'artifact'"))
        self.artifact = artifact
        self.url = url
        self.relative_path = relative_path
        self.remote = remote


class DeclarativeContent:
    """
    Relates a Content unit and zero or more DeclarativeArtifact objects.

    This is used by the Stages API stages to determine if a Content unit is already present and
    ensure all of its associated DeclarativeArtifact objects are related correctly. The `content`
    can be either saved or unsaved depending on where in the Stages API pipeline this is used.

    Attributes:
        content - The in-memory, partial Artifact with any known digest information attached to it
        d_artifacts - A list of zero or more DeclarativeArtifacts associated with `content`.

    Raises:
        ValueError: If `content` is not specified.
    """

    __slots__ = ('content', 'd_artifacts')

    def __init__(self, content=None, d_artifacts=None):
        if not content:
            raise ValueError(_("DeclarativeContent must have a 'content'"))
        if d_artifacts:
            self.d_artifacts = d_artifacts
        else:
            self.d_artifacts = []
        self.content = content
