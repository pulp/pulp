import asyncio
import logging

from django.db.models import Q

from pulpcore.plugin.models import Artifact, ProgressBar

from .api import Stage

log = logging.getLogger(__name__)


class QueryExistingArtifacts(Stage):
    """
    A Stages API stage that replaces :attr:`DeclarativeContent.content` objects with already-saved
    :class:`~pulpcore.plugin.models.Artifact` objects.

    This stage expects :class:`~pulpcore.plugin.stages.DeclarativeContent` units from `in_q` and
    inspects their associated :class:`~pulpcore.plugin.stages.DeclarativeArtifact` objects. Each
    :class:`~pulpcore.plugin.stages.DeclarativeArtifact` object stores one
    :class:`~pulpcore.plugin.models.Artifact`.

    This stage inspects any unsaved :class:`~pulpcore.plugin.models.Artifact` objects and searches
    using their metadata for existing saved :class:`~pulpcore.plugin.models.Artifact` objects inside
    Pulp with the same digest value(s). Any existing :class:`~pulpcore.plugin.models.Artifact`
    objects found will replace their unsaved counterpart in the
    :class:`~pulpcore.plugin.stages.DeclarativeArtifact` object.

    Each :class:`~pulpcore.plugin.stages.DeclarativeContent` is sent to `out_q` after all of its
    :class:`~pulpcore.plugin.stages.DeclarativeArtifact` objects have been handled.

    This stage drains all available items from `in_q` and batches everything into one large call to
    the db for efficiency.
    """

    async def __call__(self, in_q, out_q):
        """
        The coroutine for this stage.

        Args:
            in_q (:class:`asyncio.Queue`): The queue to receive
                :class:`~pulpcore.plugin.stages.DeclarativeContent` objects from.
            out_q (:class:`asyncio.Queue`): The queue to put
                :class:`~pulpcore.plugin.stages.DeclarativeContent` into.

        Returns:
            The coroutine for this stage.
        """
        async for batch in self.batches(in_q):
            all_artifacts_q = Q(pk=None)
            for content in batch:
                for declarative_artifact in content.d_artifacts:
                    one_artifact_q = declarative_artifact.artifact.q()
                    if one_artifact_q:
                        all_artifacts_q |= one_artifact_q

            for artifact in Artifact.objects.filter(all_artifacts_q):
                for content in batch:
                    for declarative_artifact in content.d_artifacts:
                        for digest_name in artifact.DIGEST_FIELDS:
                            digest_value = getattr(declarative_artifact.artifact, digest_name)
                            if digest_value and digest_value == getattr(artifact, digest_name):
                                declarative_artifact.artifact = artifact
                                break
            for content in batch:
                await out_q.put(content)
        await out_q.put(None)


class ArtifactDownloaderRunner():
    """
    This class encapsulates an actual run of the ArtifactDownloader stage.

    As there is a lot of state to keep during the run, a run is modelled as an
    instance of :class:`ArtifactDownloaderRunner` which stores the state as
    instance members.

    Call `run()` to actually do the work.

    Args:
        in_q (:class:`asyncio.Queue`): The queue to receive
                :class:`~pulpcore.plugin.stages.DeclarativeContent` objects from.
        out_q (:class:`asyncio.Queue`): The queue to put
                :class:`~pulpcore.plugin.stages.DeclarativeContent` objects into.
        max_concurrent_content (int): The maximum number of
            :class:`~pulpcore.plugin.stages.DeclarativeContent` instances to handle simultaneously.
    """

    def __init__(self, in_q, out_q, max_concurrent_content):
        self.in_q = in_q
        self.out_q = out_q
        self.max_concurrent_content = max_concurrent_content

    @property
    def saturated(self):
        return len(self._pending) >= self.max_concurrent_content

    @property
    def shutdown(self):
        return self._content_get_task is None

    async def run(self):
        """
        The coroutine doing the stage's work.
        """
        #: (set): The set of unfinished tasks.  Contains the content
        #    handler tasks and may contain `self._content_get_task`.
        self._pending = set()

        #: (:class:`asyncio.Task`): The task that gets new content from `in_q`.
        #    Set to None if stage is shutdown.
        self._content_get_task = self._add_to_pending(self.in_q.get())

        with ProgressBar(message='Downloading Artifacts') as pb:
            try:
                while self._pending:
                    done, self._pending = await asyncio.wait(self._pending,
                                                             return_when=asyncio.FIRST_COMPLETED)
                    for task in done:
                        if task is self._content_get_task:
                            content = task.result()
                            if content is None:
                                # previous stage is finished and we retrieved all
                                # content instances: shutdown
                                self._content_get_task = None
                            else:
                                self._add_to_pending(self._handle_content_unit(content))
                        else:
                            download_count = task.result()
                            pb.done += download_count
                            pb.save()

                    if not self.shutdown:
                        if not self.saturated and self._content_get_task not in self._pending:
                            self._content_get_task = self._add_to_pending(self.in_q.get())
            except asyncio.CancelledError:
                # asyncio.wait does not cancel its tasks when cancelled, we need to do this
                for future in self._pending:
                    future.cancel()
                raise

        await self.out_q.put(None)

    def _add_to_pending(self, coro):
        task = asyncio.ensure_future(coro)
        self._pending.add(asyncio.ensure_future(task))
        return task

    async def _handle_content_unit(self, content):
        """Handle one content unit.

        Returns:
            The number of downloads
        """
        downloaders_for_content = self._downloaders_for_content(content)
        if downloaders_for_content:
            downloads = await asyncio.gather(*downloaders_for_content)
            self._update_content(content, downloads)
        await self.out_q.put(content)
        return len(downloaders_for_content)

    def _downloaders_for_content(self, content):
        """
        Compute a list of downloader coroutines, one for each artifact to download for `content`.

        Returns:
            List of downloader coroutines (may be empty)
        """
        downloaders_for_content = []
        for declarative_artifact in content.d_artifacts:
            if declarative_artifact.artifact.pk is None:
                # this needs to be downloaded
                expected_digests = {}
                validation_kwargs = {}
                for digest_name in declarative_artifact.artifact.DIGEST_FIELDS:
                    digest_value = getattr(declarative_artifact.artifact, digest_name)
                    if digest_value:
                        expected_digests[digest_name] = digest_value
                if expected_digests:
                    validation_kwargs['expected_digests'] = expected_digests
                if declarative_artifact.artifact.size:
                    expected_size = declarative_artifact.artifact.size
                    validation_kwargs['expected_size'] = expected_size
                downloader = declarative_artifact.remote.get_downloader(
                    url=declarative_artifact.url,
                    **validation_kwargs
                )
                # Custom downloaders may need extra information to complete the request.
                downloaders_for_content.append(
                    downloader.run(extra_data=declarative_artifact.extra_data)
                )

        return downloaders_for_content

    def _update_content(self, content, downloads):
        """Update the content using the download results."""
        for download_result in downloads:

            def url_lookup(x):
                return x.url == download_result.url
            d_artifact = list(filter(url_lookup, content.d_artifacts))[0]
            if d_artifact.artifact.pk is None:
                new_artifact = Artifact(
                    **download_result.artifact_attributes,
                    file=download_result.path
                )
                d_artifact.artifact = new_artifact


class ArtifactDownloader(Stage):
    """
    A Stages API stage to download :class:`~pulpcore.plugin.models.Artifact` files, but don't save
    the :class:`~pulpcore.plugin.models.Artifact` in the db.

    This stage downloads the file for any :class:`~pulpcore.plugin.models.Artifact` objects missing
    files and creates a new :class:`~pulpcore.plugin.models.Artifact` object from the downloaded
    file and its digest data. The new :class:`~pulpcore.plugin.models.Artifact` is not saved but
    added to the :class:`~pulpcore.plugin.stages.DeclarativeArtifact` object, replacing the likely
    incomplete :class:`~pulpcore.plugin.models.Artifact`.

    Each :class:`~pulpcore.plugin.stages.DeclarativeContent` is sent to `out_q` after all of its
    :class:`~pulpcore.plugin.stages.DeclarativeArtifact` objects have been handled.

    This stage creates a ProgressBar named 'Downloading Artifacts' that counts the number of
    downloads completed. Since it's a stream the total count isn't known until it's finished.

    This stage drains all available items from `in_q` and starts as many downloaders as possible
    (up to `connection_limit` set on a Remote)

    Args:
        max_concurrent_content (int): The maximum number of
            :class:`~pulpcore.plugin.stages.DeclarativeContent` instances to handle simultaneously.
            Default is 200.
        args: unused positional arguments passed along to :class:`~pulpcore.plugin.stages.Stage`.
        kwargs: unused keyword arguments passed along to :class:`~pulpcore.plugin.stages.Stage`.
    """

    def __init__(self, max_concurrent_content=200, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_concurrent_content = max_concurrent_content

    async def __call__(self, in_q, out_q):
        """
        The coroutine for this stage.

        Args:
            in_q (:class:`asyncio.Queue`): The queue to receive
                :class:`~pulpcore.plugin.stages.DeclarativeContent` objects from that may have
                undownloaded files.
            out_q (:class:`asyncio.Queue`): The queue to put
                :class:`~pulpcore.plugin.stages.DeclarativeContent` objects into, all of which have
                files downloaded.

        Returns:
            The coroutine for this stage.
        """
        runner = ArtifactDownloaderRunner(in_q, out_q, self.max_concurrent_content)
        await runner.run()


class ArtifactSaver(Stage):
    """
    A Stages API stage that saves any unsaved :attr:`DeclarativeArtifact.artifact` objects.

    This stage expects :class:`~pulpcore.plugin.stages.DeclarativeContent` units from `in_q` and
    inspects their associated :class:`~pulpcore.plugin.stages.DeclarativeArtifact` objects. Each
    :class:`~pulpcore.plugin.stages.DeclarativeArtifact` object stores one
    :class:`~pulpcore.plugin.models.Artifact`.

    Any unsaved :class:`~pulpcore.plugin.models.Artifact` objects are saved. Each
    :class:`~pulpcore.plugin.stages.DeclarativeContent` is sent to `out_q` after all of its
    :class:`~pulpcore.plugin.stages.DeclarativeArtifact` objects have been handled.

    This stage drains all available items from `in_q` and batches everything into one large call to
    the db for efficiency.
    """

    async def __call__(self, in_q, out_q):
        """
        The coroutine for this stage.

        Args:
            in_q (:class:`asyncio.Queue`): The queue to receive
                :class:`~pulpcore.plugin.stages.DeclarativeContent` objects from.
            out_q (:class:`asyncio.Queue`): The queue to put
                :class:`~pulpcore.plugin.stages.DeclarativeContent` into.

        Returns:
            The coroutine for this stage.
        """
        async for batch in self.batches(in_q):
            da_to_save = []
            for declarative_content in batch:
                for declarative_artifact in declarative_content.d_artifacts:
                    if declarative_artifact.artifact.pk is None:
                        declarative_artifact.artifact.file = str(declarative_artifact.artifact.file)
                        da_to_save.append(declarative_artifact)

            if da_to_save:
                for da, artifact in zip(da_to_save, Artifact.objects.bulk_get_or_create(
                        da.artifact for da in da_to_save)):
                    da.artifact = artifact

            for declarative_content in batch:
                await out_q.put(declarative_content)

        await out_q.put(None)
