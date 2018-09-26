from gettext import gettext as _


class DeclarativeArtifact:
    """
    Relates an :class:`~pulpcore.plugin.models.Artifact`, how to download it, and its
    `relative_path` used later during publishing.

    This is used by the Stages API stages to determine if an
    :class:`~pulpcore.plugin.models.Artifact` is already present and ensure Pulp can download it in
    the future. The `artifact` can be either saved or unsaved. If unsaved, the `artifact` attributes
    may be incomplete because not all digest information can be computed until the
    :class:`~pulpcore.plugin.models.Artifact` is downloaded.

    Attributes:
        artifact (:class:`~pulpcore.plugin.models.Artifact`): An
            :class:`~pulpcore.plugin.models.Artifact` either saved or unsaved. If unsaved, it
            may have partial digest information attached to it.
        url (str): the url to fetch the :class:`~pulpcore.plugin.models.Artifact` from.
        relative_path (str): the relative_path this :class:`~pulpcore.plugin.models.Artifact`
            should be published at for any Publication.
        remote (:class:`~pulpcore.plugin.models.Remote`): The remote used to fetch this
            :class:`~pulpcore.plugin.models.Artifact`.
        extra_data (dict): A dictionary available for additional data to be stored in.

    Raises:
        ValueError: If `artifact`, `url`, `relative_path`, or `remote` are not specified.
    """

    __slots__ = ('artifact', 'url', 'relative_path', 'remote', 'extra_data')

    def __init__(self, artifact=None, url=None, relative_path=None, remote=None, extra_data=None):
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
        self.extra_data = extra_data or {}


class DeclarativeContent:
    """
    Relates a Content unit and zero or more :class:`~pulpcore.plugin.stages.DeclarativeArtifact`
    objects.

    This is used by the Stages API stages to determine if a Content unit is already present and
    ensure all of its associated :class:`~pulpcore.plugin.stages.DeclarativeArtifact` objects are
    related correctly. The `content` can be either saved or unsaved depending on where in the Stages
    API pipeline this is used.

    Attributes:
        content (subclass of :class:`~pulpcore.plugin.models.Content`): A Content unit, possibly
            unsaved
        d_artifacts (list): A list of zero or more
            :class:`~pulpcore.plugin.stages.DeclarativeArtifact` objects associated with `content`.
        extra_data (dict): A dictionary available for additional data to be stored in.

    Raises:
        ValueError: If `content` is not specified.
    """

    __slots__ = ('content', 'd_artifacts', 'extra_data')

    def __init__(self, content=None, d_artifacts=None, extra_data=None):
        if not content:
            raise ValueError(_("DeclarativeContent must have a 'content'"))
        self.content = content
        self.d_artifacts = d_artifacts or []
        self.extra_data = extra_data or {}
