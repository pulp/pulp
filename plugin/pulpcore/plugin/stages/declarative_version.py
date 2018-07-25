import asyncio
from gettext import gettext as _

from pulpcore.plugin.models import RepositoryVersion
from pulpcore.plugin.tasking import WorkingDirectory

from .api import create_pipeline, end_stage
from .artifact_stages import artifact_downloader, artifact_saver, query_existing_artifacts
from .association_stages import content_unit_association, content_unit_unassociation
from .content_unit_stages import content_unit_saver, query_existing_content_units


class FirstStage:
    """
    A class plugin writers can subclass and use as the first stage for a DeclarativeVersion pipeline

    To use this class, the plugin writer needs to:

    1. Subclass it and implement the `gen_declarative_content()` method.
    2. Pass the instantiated subclass to `DeclarativeVersion`.
    """

    async def gen_declarative_content(self, in_q, out_q):
        """
        A Stages API compatible coroutine for `DeclarativeVersion` to use as the first stage.

        This must be implemented on the subclass.

        Args:
            in_q (asyncio.Queue): Unused because the first stage doesn't read from an input queue.
            out_q (asyncio.Queue): The queue to put `DeclarativeContent` into.

        Returns:
            A Stages API compatible coroutine for `DeclarativeVersion` to use as the first stage.
        """
        raise NotImplementedError('A plugin writer needs to implement this')


class DeclarativeVersion:

    def __init__(self, first_stage, repository, sync_mode='mirror'):
        """
        A pipeline that creates a new RepositoryVersion from a stream of DeclarativeContent objects.

        The plugin writer needs to specify a first_stage that will create a
        `~pulpcore.plugin.stages.DeclarativeContent` object for each Content unit that should exist
        in the new RepositoryVersion.

        The pipeline stages perform the following steps:

        1. Create the new RespositoryVersion
        2. Query existing artifacts to determine which are already local to Pulp
        3. Download the undownloaded Artifacts
        4. Save the newly downloaded Artifacts
        5. Query for content units already present in Pulp
        6. Save new content units not yet present in Pulp
        7. Associate all content units with the new repository version.
        8. Unassociate any content units not declared in the stream (only when sync_mode='mirror')

        To do this, the plugin writer should subclass the FirstStage class and define its
        `gen_declarative_content()` interface which return a coroutine. This coroutine should
        download metadata, create the corresponding DeclarativeContent objects, and put them into
        the `asyncio.Queue` to send them down the pipeline. For example:

        >>> class MyFirstStage(FirstStage):
        >>>
        >>>     def __init__(remote):
        >>>         self.remote = remote
        >>>
        >>>     async def gen_declarative_content(self, out_q):
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
        to `DeclarativeVersion`.

        1. Create the instance of the FirstStage subclass
        2. Create the `DeclarativeVersion` instance, passing the FirstStage subclass instance to it
        3. Call the `create()` method on your `DeclarativeVersion` instance

        Here is an example:

        >>> first_stage = FileFirstStage(remote)
        >>> DeclarativeVersion(first_stage, repository).create()

        Args:
             first_stage (FirstStage): The first stage to receive `DeclarativeContent` from
             repository (Repository): The repository receiving the new version
             sync_mode (str): 'mirror' removes content units from the RepositoryVersion that are not
                 queued to DeclarativeVersion. 'additive' only adds content units queued to
                 DeclarativeVersion, and does not remove any pre-existing units in the
                 RepositoryVersion. 'mirror' is the default.

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
                    self.first_stage.gen_declarative_content,
                    query_existing_artifacts, artifact_downloader().stage, artifact_saver,
                    query_existing_content_units, content_unit_saver,
                    content_unit_association(new_version).stage
                ]
                if self.sync_mode is 'additive':
                    stages.append(end_stage)
                elif self.sync_mode is 'mirror':
                    stages.extend([content_unit_unassociation(new_version).stage, end_stage])
                pipeline = create_pipeline(stages)
                loop.run_until_complete(pipeline)
