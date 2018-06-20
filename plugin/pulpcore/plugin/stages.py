import asyncio

from collections import namedtuple

from django.db.models import Q

from pulpcore.plugin.tasking import WorkingDirectory
from pulpcore.plugin.models import Artifact, ContentArtifact, RepositoryVersion


DeclarativeArtifact = namedtuple('DeclarativeArtifact', ['artifact', 'url', 'relative_path', 'remote'])

DeclarativeContent = namedtuple('DeclarativeContent', ['content', 'artifacts'])


async def queue_run_stages(stages, in_q=None):
    futures = []
    for stage in stages:
        out_q = asyncio.Queue(maxsize=2)
        futures.append(stage(in_q, out_q))
        in_q = out_q
    await asyncio.gather(*futures)


class ArtifactDownloaderStage:
    """Stage that runs do_work() concurrently (with limited concurrency)."""

    def __init__(self, max_concurrent=2):
        self.max_concurrent = max_concurrent

    async def run(self, in_q, out_q):
        self._pending = set()
        self._schedule_next_future(in_q)
        saturated = False
        try:
            while self._pending:
                done, self._pending = await asyncio.wait(self._pending, return_when=asyncio.FIRST_COMPLETED)
                for future in done:
                    if future is self._next_future:
                        # The input queue yielded a new Content object.
                        assert not saturated
                        content = future.result()
                        if content:
                            self._schedule_work(content)
                            if len(self._pending) < self.max_concurrent:
                                self._schedule_next_future(in_q)
                            else:
                                saturated = True
                                self._next_future = None
                                print_t("queue_stage_concurrent: Stop getting new upstream items")
                        else:
                            # input stream depleted
                            continue
                    else:
                        # One of our workers has finished
                        await out_q.put(future.result())
                        if saturated:
                            self._schedule_next_future(in_q)
                            print_t("queue_stage_concurrent: Start getting new upstream items again")
                            saturated = False
            await out_q.put(None)
        except asyncio.CancelledError:
            # asyncio.wait does not cancel its tasks when cancelled, we need to do this
            self._cancel_pending()
            raise


    def _schedule_next_future(self, in_q):
        """Schedule getting the next item from the in queue in_q."""
        self._next_future = asyncio.ensure_future(in_q.get())
        self._pending.add(self._next_future)

    def _schedule_work(self, content):
        print_t(f"queue_stage_concurrent: Adding '{content}' to pending Futures")
        future = asyncio.ensure_future(content.do_work())
        self._pending.add(future)

    def _cancel_pending(self):
        for future in self._pending:
            future.cancel()


async def query_existing_artifacts(in_q, out_q):
    """Batch query for existing Artifacts, attach to Content unit in memory, and send to out_q"""
    await asyncio.sleep(4)  # TODO remove me. temporary to allow the queue to build up the batch
    declarative_content = []
    while True:
        try:
            content = in_q.get_nowait()
        except asyncio.QueueEmpty:
            if not declarative_content:
                await asyncio.sleep(0.5)
                continue
        else:
            declarative_content.append(content)
            continue

        all_artifacts_q = Q(pk=None)
        for content in declarative_content:
            if content is None:
                # the producer emits None to indicate that it is done
                break

            for declarative_artifact in content.artifacts:
                one_artifact_q = Q()
                for digest_name in declarative_artifact.artifact.DIGEST_FIELDS:
                    digest_value = getattr(declarative_artifact.artifact, digest_name)
                    if digest_value:
                        key = {digest_name: digest_value}
                        one_artifact_q &= Q(**key)
                all_artifacts_q |= one_artifact_q

        for artifact in Artifact.objects.filter(all_artifacts_q):
            1+1  # TODO overwrite Artifact results onto declarative_content.artifacts
            1+1
        for content in declarative_content:
            await out_q.put(content)
        declarative_content = []
    await out_q.put(None)


async def artifact_downloader(in_q, out_q):
    """For each DeclarativeArtifact object, download and replace it with an unsaved Artifact"""
    await asyncio.sleep(6)
    pending = set()
    incoming_content = []
    shutdown = False
    while True:
        try:
            content = in_q.get_nowait()
        except asyncio.QueueEmpty:
            if not incoming_content and not shutdown and not pending:
                await asyncio.sleep(0.2)
                continue
        else:
            incoming_content.append(content)
            continue

        for content in incoming_content:
            if content is None:
                shutdown = True
                continue
            downloaders_for_content = []
            for artifact_or_da in content.artifacts:
                if isinstance(artifact_or_da, DeclarativeArtifact):
                    # this needs to be downloaded
                    downloader = artifact_or_da.remote.get_downloader(artifact_or_da.url)
                    next_future = asyncio.ensure_future(downloader.run())
                    downloaders_for_content.append(next_future)
            if not downloaders_for_content:
                await out_q.put(content)
                continue
            async def return_content_for_downloader(c):
                return c
            downloaders_for_content.append(return_content_for_downloader(content))
            pending.add(asyncio.gather(*downloaders_for_content))
        incoming_content = []

        if pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for gathered_downloaders in done:
                results = gathered_downloaders.result()
                for download_result in results[:-1]:
                    content = results[-1]
                    for i, artifact_or_da in enumerate(content.artifacts):
                        if isinstance(artifact_or_da, DeclarativeArtifact):
                            attributes = download_result.artifact_attributes
                            content.artifacts[i] = Artifact(**attributes)
                    await out_q.put(content)
    await out_q.put(None)


async def artifact_saver(in_q, out_q):
    """For each Artifact ensure it is saved"""
    while True:
        declarative_content = await in_q.get()
        if declarative_content is None:
            break
        for artifact in declarative_content.artifacts:
            artifact.save()
        await out_q.put(declarative_content)
    await out_q.put(None)


async def query_existing_content_units(in_q, out_q):
    """Batch query for existing Content Units, to Content unit in memory, and send to out_q"""
    await asyncio.sleep(10)
    import pydevd
    pydevd.settrace('localhost', port=29437, stdoutToServer=True, stderrToServer=True)
    declarative_content = []
    while True:
        try:
            content = in_q.get_nowait()
        except asyncio.QueueEmpty:
            if not declarative_content:
                await asyncio.sleep(0.5)
                continue
        else:
            declarative_content.append(content)
            continue

        all_artifacts_q = Q(pk=None)
        for content in declarative_content:
            if content is None:
                # the producer emits None to indicate that it is done
                break

            for declarative_artifact in content.artifacts:
                one_artifact_q = Q()
                for digest_name in declarative_artifact.artifact.DIGEST_FIELDS:
                    digest_value = getattr(declarative_artifact.artifact, digest_name)
                    if digest_value:
                        key = {digest_name: digest_value}
                        one_artifact_q &= Q(**key)
                all_artifacts_q |= one_artifact_q

        for artifact in Artifact.objects.filter(all_artifacts_q):
            1+1  # TODO overwrite Artifact results onto declarative_content.artifacts
            1+1
        for content in declarative_content:
            await out_q.put(content)
        declarative_content = []
    await out_q.put(None)


class DeclarativeVersion:

    stages = [query_existing_artifacts, artifact_downloader, artifact_saver,
              query_existing_content_units]

    def __init__(self, in_q, repository, remote, sync_mode='mirror'):
        """

        Args:
             first_stage (coroutine): The coroutine
        """
        self.in_q = in_q
        self.repository = repository
        self.remote = remote
        self.sync_mode = sync_mode

    def create(self):
        with WorkingDirectory():
            with RepositoryVersion.create(self.repository) as new_version:
                loop = asyncio.get_event_loop()
                pipeline = queue_run_stages(
                    DeclarativeVersion.stages, self.in_q
                )
                loop.run_until_complete(pipeline)
