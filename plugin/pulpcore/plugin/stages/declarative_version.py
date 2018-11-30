import asyncio

from pulpcore.plugin.models import RepositoryVersion
from pulpcore.plugin.tasking import WorkingDirectory

from .api import create_pipeline, EndStage
from .artifact_stages import ArtifactDownloader, ArtifactSaver, QueryExistingArtifacts
from .association_stages import ContentUnitAssociation, ContentUnitUnassociation
from .content_unit_stages import ContentUnitSaver, QueryExistingContentUnits


class DeclarativeVersion:

    def __init__(self, first_stage, repository, mirror=True, download_artifacts=True):
        """
        A pipeline that creates a new :class:`~pulpcore.plugin.models.RepositoryVersion` from a
        stream of :class:`~pulpcore.plugin.stages.DeclarativeContent` objects.

        The plugin writer needs to specify a first_stage that will create a
        :class:`~pulpcore.plugin.stages.DeclarativeContent` object for each Content unit that should
        exist in the new :class:`~pulpcore.plugin.models.RepositoryVersion`.

        The pipeline stages perform the following steps by default:

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
        :class:`~pulpcore.plugin.stages.Stage` class and define its
        :meth:`__call__()` interface which returns a coroutine. This coroutine should
        download metadata, create the corresponding
        :class:`~pulpcore.plugin.stages.DeclarativeContent` objects, and put them into the
        :class:`asyncio.Queue` to send them down the pipeline. For example:

        >>> class MyFirstStage(Stage):
        >>>
        >>>     def __init__(remote):
        >>>         self.remote = remote
        >>>
        >>>     async def __call__(self, out_q):
        >>>         downloader = remote.get_downloader(url=remote.url)
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

        1. Create the instance of the subclassed :class:`~pulpcore.plugin.stages.Stage` object.
        2. Create the :class:`~pulpcore.plugin.stages.DeclarativeVersion` instance, passing the
           :class:`~pulpcore.plugin.stages.Stage` subclass instance to it
        3. Call the :meth:`~pulpcore.plugin.stages.DeclarativeVersion.create` method on your
           :class:`~pulpcore.plugin.stages.DeclarativeVersion` instance

        Here is an example:

        >>> first_stage = MyFirstStage(remote)
        >>> DeclarativeVersion(first_stage, repository).create()

        Args:
             first_stage (:class:`~pulpcore.plugin.stages.Stage`): The first stage to receive
                 :class:`~pulpcore.plugin.stages.DeclarativeContent` from.
             repository (:class:`~pulpcore.plugin.models.Repository`): The repository receiving the
                 new version.
             mirror (bool): 'True' removes content units from the
                 :class:`~pulpcore.plugin.models.RepositoryVersion` that are not
                 requested in the :class:`~pulpcore.plugin.stages.DeclarativeVersion` stream.
                 'False' (additive) only adds content units observed in the
                 :class:`~pulpcore.plugin.stages.DeclarativeVersion stream`, and does not remove any
                 pre-existing units in the :class:`~pulpcore.plugin.models.RepositoryVersion`.
                 'True' is the default.
             download_artifacts (bool): 'True' includes Artifact downloading and saving along with
                 content unit query and saving. 'False' will only handle content units and will not
                 perform Artifact downloading and saving as part of the pipeline. 'False' is the
                 default.
        """
        self.first_stage = first_stage
        self.repository = repository
        self.mirror = mirror
        self.download_artifacts = download_artifacts

    def pipeline_stages(self, new_version):
        """
        Build the list of pipeline stages feeding into the ContentUnitAssociation stage.

        If the `self.download_artifacts` is False the pipeline will not include Artifact downloading
        and saving stages.

        Plugin-writers may override this method to build a custom pipeline. This
        can be achieved by returning a list with different stages or by extending
        the list returned by this method.

        Args:
            new_version (:class:`~pulpcore.plugin.models.RepositoryVersion`): The
                new repository version that is going to be built.

        Returns:
            list: List of :class:`~pulpcore.plugin.stages.Stage` instances

        """
        pipeline = [self.first_stage]
        if self.download_artifacts:
            pipeline.extend([QueryExistingArtifacts(), ArtifactDownloader(), ArtifactSaver()])
        pipeline.extend([QueryExistingContentUnits(), ContentUnitSaver()])
        return pipeline

    def create(self):
        """
        Perform the work. This is the long-blocking call where all syncing occurs.
        """
        with WorkingDirectory():
            with RepositoryVersion.create(self.repository) as new_version:
                loop = asyncio.get_event_loop()
                stages = self.pipeline_stages(new_version)
                stages.append(ContentUnitAssociation(new_version))
                if self.mirror:
                    stages.append(ContentUnitUnassociation(new_version))
                stages.append(EndStage())
                pipeline = create_pipeline(stages)
                loop.run_until_complete(pipeline)
