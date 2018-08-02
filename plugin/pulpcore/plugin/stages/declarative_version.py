import asyncio
from gettext import gettext as _

from pulpcore.plugin.models import RepositoryVersion
from pulpcore.plugin.tasking import WorkingDirectory

from .api import create_pipeline, EndStage
from .artifact_stages import ArtifactDownloader, ArtifactSaver, QueryExistingArtifacts
from .association_stages import ContentUnitAssociation, ContentUnitUnassociation
from .content_unit_stages import ContentUnitSaver, QueryExistingContentUnits


class FirstStage:
    """
    Plugin writers subclass this to create their first stage for a
    :class:`~pulpcore.plugin.stages.DeclarativeVersion` pipeline.

    To use this class, the plugin writer needs to:

    1. Subclass it and implement the
       :meth:`~pulpcore.plugin.stages.FirstStage.__call__` method.
    2. Pass the instantiated subclass to :class:`~pulpcore.plugin.stages.DeclarativeVersion`.
    """

    async def __call__(self, in_q, out_q):
        """
        A Stages API compatible coroutine for :class:`~pulpcore.plugin.stages.DeclarativeVersion` to
        use as the first stage.

        This must be implemented on the subclass.

        Args:
            in_q (:class:`asyncio.Queue`): Unused because the first stage doesn't read from an input
                queue.
            out_q (:class:`asyncio.Queue`): The queue to put
                :class:`~pulpcore.plugin.stages.DeclarativeContent` into.

        Returns:
            A Stages API compatible coroutine for
            :class:`~pulpcore.plugin.stages.DeclarativeVersion` to use as the first stage.
        """
        raise NotImplementedError('A plugin writer needs to implement this')


class DeclarativeVersion:

    def __init__(self, first_stage, repository, sync_mode='mirror'):
        """
        A pipeline that creates a new :class:`~pulpcore.plugin.models.RepositoryVersion` from a
        stream of :class:`~pulpcore.plugin.stages.DeclarativeContent` objects.

        The plugin writer needs to specify a first_stage that will create a
        :class:`~pulpcore.plugin.stages.DeclarativeContent` object for each Content unit that should
        exist in the new :class:`~pulpcore.plugin.models.RepositoryVersion`.

        The pipeline stages perform the following steps:

        1. Create the new :class:`~pulpcore.plugin.models.RepositoryVersion`
        2. Query existing artifacts to determine which are already local to Pulp
        3. Download any undownloaded :class:`~pulpcore.plugin.models.Artifact` objects.
        4. Save the newly downloaded :class:`~pulpcore.plugin.models.Artifact` objects
        5. Query for Content units already present in Pulp
        6. Save new Content units not yet present in Pulp
        7. Associate all content units with the new
           :class:`~pulpcore.plugin.models.RepositoryVersion`.
        8. Unassociate any content units not declared in the stream (only when sync_mode='mirror')

        To do this, the plugin writer should subclass the
        :class:`~pulpcore.plugin.stages.FirstStage` class and define its
        :meth:`__call__()` interface which return a coroutine. This coroutine should
        download metadata, create the corresponding
        :class:`~pulpcore.plugin.stages.DeclarativeContent` objects, and put them into the
        :class:`asyncio.Queue` to send them down the pipeline. For example:

        >>> class MyFirstStage(FirstStage):
        >>>
        >>>     def __init__(remote):
        >>>         self.remote = remote
        >>>
        >>>     async def __call__(self, out_q):
        >>>         downloader = remote.get_downloader(remote.url)
        >>>         result = await downloader.run()
        >>>         for entry in read_my_metadata_file_somehow(result.path)
        >>>             unit = MyContent(entry)  # make the content unit in memory-only
        >>>             artifact = Artifact(entry)  # make Artifact in memory-only
        >>>             da = DeclarativeArtifact(artifact, url, entry.relative_path, self.remote)
        >>>             dc = DeclarativeContent(content=unit, d_artifacts=[da])
        >>>             await out_q.put(dc)
        >>>         await out_q.put(None)

        To use your first stage with the pipeline you have to instantiate the subclass and pass it
        to :class:`~pulpcore.plugin.stages.DeclarativeVersion`.

        1. Create the instance of the :class:`~pulpcore.plugin.stages.FirstStage` object subclass
        2. Create the :class:`~pulpcore.plugin.stages.DeclarativeVersion` instance, passing the
           :class:`~pulpcore.plugin.stages.FirstStage` subclass instance to it
        3. Call the :meth:`~pulpcore.plugin.stages.DeclarativeVersion.create` method on your
           :class:`~pulpcore.plugin.stages.DeclarativeVersion` instance

        Here is an example:

        >>> first_stage = FileFirstStage(remote)
        >>> DeclarativeVersion(first_stage, repository).create()

        Args:
             first_stage (:class:`~pulpcore.plugin.stages.FirstStage`): The first stage to receive
                 :class:`~pulpcore.plugin.stages.DeclarativeContent` from.
             repository (:class:`~pulpcore.plugin.models.Repository`): The repository receiving the
                 new version.
             sync_mode (str): 'mirror' removes content units from the
                 :class:`~pulpcore.plugin.models.RepositoryVersion` that are not
                 requested in the :class:`~pulpcore.plugin.stages.DeclarativeVersion` stream.
                 'additive' only adds content units observed in the
                 :class:`~pulpcore.plugin.stages.DeclarativeVersion stream`, and does not remove any
                 pre-existing units in the :class:`~pulpcore.plugin.models.RepositoryVersion`.
                 'mirror' is the default.

        Raises:
            ValueError: if 'sync_mode' is passed an invalid value.
        """
        if sync_mode is not 'mirror' and sync_mode is not 'additive':
            msg = _("'sync_mode' must either be 'mirror' or 'additive' not '{sync_mode}'")
            raise ValueError(msg.format(sync_mode=sync_mode))
        self.first_stage = first_stage
        self.repository = repository
        self.sync_mode = sync_mode

    def create(self):
        """
        Perform the work. This is the long-blocking call where all syncing occurs.
        """
        with WorkingDirectory():
            with RepositoryVersion.create(self.repository) as new_version:
                loop = asyncio.get_event_loop()
                stages = [
                    self.first_stage,
                    QueryExistingArtifacts(), ArtifactDownloader(), ArtifactSaver(),
                    QueryExistingContentUnits(), ContentUnitSaver(),
                    ContentUnitAssociation(new_version)
                ]
                if self.sync_mode is 'additive':
                    stages.append(EndStage())
                elif self.sync_mode is 'mirror':
                    stages.extend([ContentUnitUnassociation(new_version), EndStage()])
                pipeline = create_pipeline(stages)
                loop.run_until_complete(pipeline)
