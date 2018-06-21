import asyncio

from collections import defaultdict, namedtuple

from django.db.models import Q

from pulpcore.plugin.tasking import WorkingDirectory
from pulpcore.plugin.models import Artifact, ContentArtifact, RemoteArtifact, RepositoryVersion


DeclarativeArtifact = namedtuple('DeclarativeArtifact', ['artifact', 'url', 'relative_path', 'remote'])

DeclarativeContent = namedtuple('DeclarativeContent', ['content', 'artifacts'])


async def queue_run_stages(stages, in_q=None):
    futures = []
    for stage in stages:
        out_q = asyncio.Queue(maxsize=100)
        futures.append(stage(in_q, out_q))
        in_q = out_q
    await asyncio.gather(*futures)


async def query_existing_artifacts(in_q, out_q):
    """Batch query for existing Artifacts, attach to Content unit in memory, and send to out_q"""
    # await asyncio.sleep(4)  # TODO remove me. temporary to allow the queue to build up the batch
    declarative_content = []
    shutdown = False
    while True:
        try:
            content = in_q.get_nowait()
        except asyncio.QueueEmpty:
            if not declarative_content:
                await asyncio.sleep(0.1)
                continue
        else:
            declarative_content.append(content)
            continue

        all_artifacts_q = Q(pk=None)
        for content in declarative_content:
            if content is None:
                shutdown = True
                continue

            for declarative_artifact in content.artifacts:
                one_artifact_q = Q()
                for digest_name in declarative_artifact.artifact.DIGEST_FIELDS:
                    digest_value = getattr(declarative_artifact.artifact, digest_name)
                    if digest_value:
                        key = {digest_name: digest_value}
                        one_artifact_q &= Q(**key)
                all_artifacts_q |= one_artifact_q

        for artifact in Artifact.objects.filter(all_artifacts_q):
            for content in declarative_content:
                if content is None:
                    continue
                for i, declarative_artifact in enumerate(content.artifacts):
                    for digest_name in artifact.DIGEST_FIELDS:
                        digest_value = getattr(declarative_artifact.artifact, digest_name)
                        if digest_value and digest_value == getattr(artifact, digest_name):
                            new_da = DeclarativeArtifact(
                                artifact=artifact, relative_path=declarative_artifact.relative_path,
                                url=declarative_artifact.url, remote=declarative_artifact.remote
                            )
                            content.artifacts[i] = new_da
        for content in declarative_content:
            await out_q.put(content)
        declarative_content = []
        if shutdown:
            break
    await out_q.put(None)


async def artifact_downloader(in_q, out_q):
    """For each DeclarativeArtifact object, download and replace it with an unsaved Artifact"""
    # await asyncio.sleep(6)
    pending = set()
    incoming_content = []
    shutdown = False
    while True:
        try:
            content = in_q.get_nowait()
        except asyncio.QueueEmpty:
            if not incoming_content and not shutdown and not pending:
                await asyncio.sleep(0.1)
                continue
        else:
            incoming_content.append(content)
            continue

        for content in incoming_content:
            if content is None:
                shutdown = True
                continue
            downloaders_for_content = []
            for declarative_artifact in content.artifacts:
                if declarative_artifact.artifact._state.adding:
                    # this needs to be downloaded
                    downloader = declarative_artifact.remote.get_downloader(
                        declarative_artifact.url
                    )
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
                    for i, declarative_artifact in enumerate(content.artifacts):
                        if declarative_artifact.artifact._state.adding:
                            attributes = download_result.artifact_attributes
                            new_da = DeclarativeArtifact(
                                artifact=Artifact(**attributes), url=declarative_artifact.url,
                                relative_path=declarative_artifact.relative_path,
                                remote=declarative_artifact.remote
                            )
                            content.artifacts[i] = new_da
                    await out_q.put(content)
        else:
            if shutdown:
                break
    await out_q.put(None)


async def artifact_saver(in_q, out_q):
    """For each Artifact ensure it is saved"""
    while True:
        declarative_content = await in_q.get()
        if declarative_content is None:
            break
        for declarative_artifact in declarative_content.artifacts:
            declarative_artifact.artifact.save()
        await out_q.put(declarative_content)
    await out_q.put(None)


async def query_existing_content_units(in_q, out_q):
    """Batch query for existing Content Units, to Content unit in memory, and send to out_q"""
    # await asyncio.sleep(10)
    declarative_content_list = []
    shutdown = False
    while True:
        try:
            content = in_q.get_nowait()
        except asyncio.QueueEmpty:
            if not declarative_content_list:
                await asyncio.sleep(0.1)
                continue
        else:
            declarative_content_list.append(content)
            continue

        content_q_by_type = defaultdict(lambda: Q(pk=None))
        for declarative_content in declarative_content_list:
            if declarative_content is None:
                shutdown = True
                continue

            unit_key = {}
            for field in declarative_content.content.natural_key_fields():
                unit_key[field] = getattr(declarative_content.content, field)
            model_type = type(declarative_content.content)
            content_q_by_type[model_type] = content_q_by_type[model_type] | Q(**unit_key)

        for model_type in content_q_by_type.keys():
            for result in model_type.objects.filter(content_q_by_type[model_type]):
                for i, declarative_content in enumerate(declarative_content_list):
                    if declarative_content is None:
                        continue
                    for field in result.natural_key_fields():
                        if getattr(declarative_content.content, field) != getattr(result, field):
                            break
                    new_dc = DeclarativeContent(
                        content=result, artifacts=declarative_content.artifacts
                    )
                    declarative_content_list[i] = new_dc
        for declarative_content in declarative_content_list:
            await out_q.put(declarative_content)
        declarative_content_list = []
        if shutdown:
            break
    await out_q.put(None)


async def content_unit_saver(in_q, out_q):
    """For each Content Unit ensure it is saved"""
    declarative_content_list = []
    while True:
        try:
            declarative_content = in_q.get_nowait()
        except asyncio.QueueEmpty:
            if not declarative_content_list:
                await asyncio.sleep(0.1)
                continue
        else:
            declarative_content_list.append(declarative_content)
            continue

        bulk_save_by_type = defaultdict(list)
        content_artifact_bulk = []
        remote_artifact_bulk = []

        for declarative_content in declarative_content_list:
            if declarative_content.content._state.adding:
                unit = declarative_content.content
                bulk_save_by_type[type(unit)].append(unit)
                for declarative_artifact in declarative_content.artifacts:
                    content_artifact = ContentArtifact(
                        content=declarative_content.content, artifact=declarative_artifact.artifact,
                        relative_path=declarative_artifact.relative_path
                    )
                    content_artifact_bulk.append(content_artifact)
                    #RemoteArtifact(content=declarative_content.content, artifact=declarative_artifact.artifact, relative_path=declarative_artifact.relative_path)
                    1+1
                    1+1


        for model_class in bulk_save_by_type.keys():
            model_class.objects.bulk_create(bulk_save_by_type[model_class])

        for declarative_content in declarative_content_list:
            if declarative_content is None:
                break
            await out_q.put(declarative_content.content)
        declarative_content_list = []
    await out_q.put(None)


def content_unit_association(new_version):
    version = new_version
    async def actual_stage(in_q, out_q):
        """For each Content Unit associate it with the repository version"""
        while True:
            content = await in_q.get()
            if content is None:
                break
            version.add_content(content)
        await out_q.put(None)
    return actual_stage



class DeclarativeVersion:

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
        # import cProfile
        # pr = cProfile.Profile()
        # pr.enable()
        import pydevd
        pydevd.settrace('localhost', port=29437, stdoutToServer=True, stderrToServer=True)
        with WorkingDirectory():
            with RepositoryVersion.create(self.repository) as new_version:
                loop = asyncio.get_event_loop()
                stages = [
                    query_existing_artifacts, artifact_downloader, artifact_saver,
                    query_existing_content_units, content_unit_saver,
                    content_unit_association(new_version)
                ]
                pipeline = queue_run_stages(
                    stages, self.in_q
                )
                loop.run_until_complete(pipeline)
        # pr.disable()
        # pr.dump_stats('/home/vagrant/devel/outputdump.profile')
