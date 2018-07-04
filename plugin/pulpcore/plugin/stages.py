import asyncio
from collections import defaultdict, namedtuple
from gettext import gettext as _

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

            model_type = type(declarative_content.content)
            unit_key = declarative_content.content.natural_key_dict()
            content_q_by_type[model_type] = content_q_by_type[model_type] | Q(**unit_key)

        for model_type in content_q_by_type.keys():
            for result in model_type.objects.filter(content_q_by_type[model_type]):
                for i, declarative_content in enumerate(declarative_content_list):
                    if declarative_content is None:
                        continue
                    not_same_unit = False
                    for field in result.natural_key_fields():
                        if getattr(declarative_content.content, field) != getattr(result, field):
                            not_same_unit = True
                            break
                    if not_same_unit:
                        continue
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
    shutdown = False
    while True:
        try:
            declarative_content = in_q.get_nowait()
        except asyncio.QueueEmpty:
            if not declarative_content_list and not shutdown:
                await asyncio.sleep(0.1)
                continue
        else:
            declarative_content_list.append(declarative_content)
            continue

        content_artifact_bulk = []
        remote_artifact_bulk = []

        for declarative_content in declarative_content_list:
            if declarative_content is None:
                shutdown = True
                continue
            if declarative_content.content._state.adding:
                # TODO add transaction here
                declarative_content.content.save()
                for declarative_artifact in declarative_content.artifacts:
                    content_artifact = ContentArtifact(
                        content=declarative_content.content, artifact=declarative_artifact.artifact,
                        relative_path=declarative_artifact.relative_path
                    )
                    content_artifact_bulk.append(content_artifact)
                    remote_artifact = RemoteArtifact(
                        url=declarative_artifact.url, size=declarative_artifact.artifact.size,
                        md5=declarative_artifact.artifact.md5,
                        sha1=declarative_artifact.artifact.sha1,
                        sha224=declarative_artifact.artifact.sha224,
                        sha256=declarative_artifact.artifact.sha256,
                        sha384=declarative_artifact.artifact.sha384,
                        sha512=declarative_artifact.artifact.sha512,
                        content_artifact=content_artifact,
                        remote=declarative_artifact.remote
                    )
                    remote_artifact_bulk.append(remote_artifact)

        ContentArtifact.objects.bulk_create(content_artifact_bulk)
        RemoteArtifact.objects.bulk_create(remote_artifact_bulk)

        for declarative_content in declarative_content_list:
            if declarative_content is None:
                continue
            await out_q.put(declarative_content.content)
        if shutdown:
            break
        declarative_content_list = []
    await out_q.put(None)


def content_unit_association(new_version):
    """
    A factory returning a Stages API stage that associates content units with `new_version`.

    This stage stores all content unit types and unit keys in memory for two reasons:

    1. Units already associated are not re-added. It would end up being ok, but it's not efficient.
    2. To compute the units already associated but not received from `in_q`. These units are passed
       via `out_q` to the next stage as a `~django.db.models.query.QuerySet`.

    in_q data type: a saved `~pulpcore.plugin.models.Content` or subclass
    out_q data type: `django.db.models.query.QuerySet`

    Args:
        new_version (RepositoryVersion): The RespositoryVersion this stage associates content with.

    Returns:
        The configured content_unit_association stage as a coroutine to be included in a pipeline.
    """
    version = new_version
    unit_keys_by_type = defaultdict(set)
    for unit in new_version.content.all():
        unit = unit.cast()
        unit_keys_by_type[type(unit)].add(unit.natural_key())
    async def actual_stage(in_q, out_q):
        """For each Content Unit associate it with the repository version"""
        while True:
            content = await in_q.get()
            if content is None:
                break
            try:
                unit_keys_by_type[type(content)].remove(content.natural_key())
            except KeyError:
                version.add_content(content)
        for unit_type, ids in unit_keys_by_type.items():
            if ids:
                units_to_unassociate = Q()
                for unit_key in unit_keys_by_type[unit_type]:
                    query_dict = {}
                    for i, key_name in enumerate(unit_type.natural_key_fields()):
                        query_dict[key_name] = unit_key[i]
                    units_to_unassociate |= Q(**query_dict)
                await out_q.put(unit_type.objects.filter(units_to_unassociate))
        await out_q.put(None)
    return actual_stage


def content_unit_unassociate(new_version):
    """
    A Stages API stage that unassociates content units from new_version.

    Args:
        new_version:

    Returns:

    """
    version = new_version
    async def actual_stage(in_q, out_q):
        """For each Content Unit from in_q, unassociate it with the repository version"""
        while True:
            queryset_to_unassociate = await in_q.get()
            if queryset_to_unassociate is None:
                break

            for unit in queryset_to_unassociate:
                version.remove_content(unit)

            await out_q.put(queryset_to_unassociate)
        await out_q.put(None)
    return actual_stage


async def end_stage(in_q, out_q):
    """
    A Stages API stage that drains `in_q` and do nothing with the items. This is expected at the end of all pipelines.

    Without this stage, the maxsize of the `out_q` from the last stage could fill up and block the
    entire pipeline.
    """
    while True:
        content = await in_q.get()
        if content is None:
            break


class DeclarativeVersion:

    def __init__(self, in_q, repository, sync_mode='mirror'):
        """
        A pipeline that creates a new RepositoryVersion from a stream of DeclarativeContent objects.

        The plugin writer needs to create a `~pulpcore.plugin.stages.DeclarativeContent` object for
        each Content unit that should exist in the new RepositoryVersion. Each
        `~pulpcore.plugin.stages.DeclarativeContent` object is put into the pipeline via the `in_q`
        object.

        The pipeline stages perform the following steps:

        1. Create the new RespositoryVersion
        2. Query existing artifacts to determine which are already local to Pulp
        3. Download the undownloaded Artifacts
        4. Save the newly downloaded Artifacts
        5. Query for content units already present in Pulp
        6. Save new content units not yet present in Pulp
        7. Associate all content units with the new repository version.
        8. Unassociate any content units not declared in the stream (only when sync_mode='mirror')

        To do this, the plugin writer should create a coroutine which downloads metadata, creates
        corresponding DeclarativeContent objects, and put them into the `asyncio.Queue` to send them
        down the pipeline. For example:

        >>> async def fetch_metadata(remote, out_q):
        >>>     downloader = remote.get_downloader(remote.url)
        >>>     result = await downloader.run()
        >>>     for entry in read_my_metadata_file_somehow(result.path)
        >>>         unit = MyContent(entry)  # make the content unit in memory-only
        >>>         artifact = Artifact(entry)  # make Artifact in memory-only
        >>>         da = DeclarativeArtifact(artifact, url, entry.relative_path, remote)
        >>>         dc = DeclarativeContent(content=unit, artifacts=[da])
        >>>         await out_q.put(dc)
        >>>     await out_q.put(None)

        To use your coroutine with the pipeline you have to:

        1. Create the asyncio.Queue the pipeline should listen on
        2. Schedule your corouine using `ensure_future()`
        3. Create the `DeclarativeVersion` and call its `create()` method

        Here is an example:

        >>> out_q = asyncio.Queue(maxsize=100)  # restricts the number of content units in memory
        >>> asyncio.ensure_future(fetch_metadata(remote, out_q))  # Schedule the "fetching" stage
        >>> DeclarativeVersion(out_q, repository).create()

        Args:
             in_q (asyncio.Queue): The queue to get DeclarativeContent from
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
        self.in_q = in_q
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
                    query_existing_artifacts, artifact_downloader, artifact_saver,
                    query_existing_content_units, content_unit_saver,
                    content_unit_association(new_version)
                ]
                if self.sync_mode is 'additive':
                    stages.append(end_stage)
                elif self.sync_mode is 'mirror':
                    stages.extend([content_unit_unassociate(new_version), end_stage])
                pipeline = queue_run_stages(stages, self.in_q)
                loop.run_until_complete(pipeline)
