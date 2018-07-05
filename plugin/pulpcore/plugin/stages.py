import asyncio
from collections import defaultdict
from gettext import gettext as _

from django.db import transaction
from django.db.models import Q

from pulpcore.plugin.tasking import WorkingDirectory
from pulpcore.plugin.models import (
    Artifact, ContentArtifact, ProgressBar, RemoteArtifact, RepositoryVersion
)


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


async def create_pipeline(stages, in_q=None, maxsize=100):
    """
    Creates a Stages API linear pipeline from the list `stages` and return as a single coroutine.

    Each stage is a coroutine and reads from an input `asyncio.Queue` and writes to an output
    `asyncio.Queue`. When the stage is ready to shutdown it writes a `None` to the output Queue.
    Here is an example of the simplest stage that only passes data.

    >>> async def my_stage(in_q, out_q):
    >>>     while True:
    >>>         item = await in_q.get()
    >>>         if item is None:  # Check if the previous stage is shutdown
    >>>             break
    >>>         await out_q.put(item)
    >>>     await out_q.put(None)  # this stage is shutdown so send 'None'

    Args:
        stages (list of coroutines): A list of Stages API compatible coroutines.
        in_q (asyncio.Queue): The queue the first stage should read from. This is how to put work
            into the pipeline. Optional especially for cases where the first stage generates items
            for `out_q` without needing inputs from `in_q`.
        maxsize (int): The maximum amount of items a queue between two stages should hold. Optional
            and defaults to 100.

    Returns:
        A single coroutine that can be used to run, wait, or cancel the entire pipeline with.
    """
    futures = []
    for stage in stages:
        out_q = asyncio.Queue(maxsize=maxsize)
        futures.append(stage(in_q, out_q))
        in_q = out_q
    await asyncio.gather(*futures)


async def query_existing_artifacts(in_q, out_q):
    """
    Stages API stage replacing DeclarativeArtifact.artifact with already-saved Artifacts.

    This stage expects `~pulpcore.plugin.stages.DeclarativeContent` units from `in_q` and inspects
    their associated `~pulpcore.plugin.stages.DeclarativeArtifact` objects. Each
    `DeclarativeArtifact` object stores one Artifact.

    This stage inspects any "unsaved" Artifact objects metadata and searches for existing saved
    Artifacts inside Pulp with the same digest value(s). Any existing Artifact objects found replace
    their "unsaved" counterpart in the `~pulpcore.plugin.stages.DeclarativeArtifact` object.

    Each `~pulpcore.plugin.stages.DeclarativeContent` is sent to `out_q` after all of its
    `~pulpcore.plugin.stages.DeclarativeArtifact` objects have been handled.

    This stage drains all available items from `in_q` and batches everything into one large call to
    the db for efficiency.

    Args:
        in_q: `~pulpcore.plugin.stages.DeclarativeContent`
        out_q: `~pulpcore.plugin.stages.DeclarativeContent`

    Returns:
        The query_existing_artifacts stage as a coroutine to be included in a pipeline.
    """
    declarative_content = []
    shutdown = False
    while True:
        try:
            content = in_q.get_nowait()
        except asyncio.QueueEmpty:
            if not declarative_content:
                content = await in_q.get()
                declarative_content.append(content)
                continue
        else:
            declarative_content.append(content)
            continue

        all_artifacts_q = Q(pk=None)
        for content in declarative_content:
            if content is None:
                shutdown = True
                continue

            for declarative_artifact in content.d_artifacts:
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
                for declarative_artifact in content.d_artifacts:
                    for digest_name in artifact.DIGEST_FIELDS:
                        digest_value = getattr(declarative_artifact.artifact, digest_name)
                        if digest_value and digest_value == getattr(artifact, digest_name):
                            declarative_artifact.artifact = artifact
        for content in declarative_content:
            await out_q.put(content)
        declarative_content = []
        if shutdown:
            break
    await out_q.put(None)


async def artifact_downloader(in_q, out_q):
    """
    Stages API stage downloading Artifact files for any "unsaved" DeclarativeArtifact.artifact.

    This stage expects `~pulpcore.plugin.stages.DeclarativeContent` units from `in_q` and inspects
    their associated `~pulpcore.plugin.stages.DeclarativeArtifact` objects. Each
    `DeclarativeArtifact` object stores one Artifact.

    This stage downloads the file for any "unsaved" Artifact object and creates a new Artifact
    from the downloaded file and its digest data. The new Artifact is *not* saved but associated
    with the `~pulpcore.plugin.stages.DeclarativeArtifact` replacing the likely incomplete Artifact.

    Each `~pulpcore.plugin.stages.DeclarativeContent` is sent to `out_q` after all of its
    `~pulpcore.plugin.stages.DeclarativeArtifact` objects have been handled.

    This stage drains all available items from `in_q` and starts as many downloaders as possible.

    Args:
        in_q: `~pulpcore.plugin.stages.DeclarativeContent`
        out_q: `~pulpcore.plugin.stages.DeclarativeContent`

    Returns:
        The artifact_downloader stage as a coroutine to be included in a pipeline.
    """
    pending = set()
    incoming_content = []
    shutdown = False
    with ProgressBar(message='Downloading Artifacts') as pb:
        while True:
            try:
                content = in_q.get_nowait()
            except asyncio.QueueEmpty:
                if not incoming_content and not shutdown and not pending:
                    content = await in_q.get()
                    incoming_content.append(content)
                    continue
            else:
                incoming_content.append(content)
                continue

            for content in incoming_content:
                if content is None:
                    shutdown = True
                    continue
                downloaders_for_content = []
                for declarative_artifact in content.d_artifacts:
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
                        for declarative_artifact in content.d_artifacts:
                            if declarative_artifact.artifact._state.adding:
                                new_artifact = Artifact(**download_result.artifact_attributes)
                                declarative_artifact.artifact = new_artifact
                                pb.increment()
                        await out_q.put(content)
            else:
                if shutdown:
                    break
    await out_q.put(None)


async def artifact_saver(in_q, out_q):
    """
    Stages API stage that saves an Artifact for any "unsaved" DeclarativeArtifact.artifact objects.

    This stage expects `~pulpcore.plugin.stages.DeclarativeContent` units from `in_q` and inspects
    their associated `~pulpcore.plugin.stages.DeclarativeArtifact` objects. Each
    `DeclarativeArtifact` object stores one Artifact.

    Any "unsaved" Artifact objects are saved. Each `~pulpcore.plugin.stages.DeclarativeContent` is
    sent to `out_q` after all of its `~pulpcore.plugin.stages.DeclarativeArtifact` objects have been
    handled.

    This stage handles items one-by-one because Artifact is not compatible with bulk_create.

    Args:
        in_q: `~pulpcore.plugin.stages.DeclarativeContent`
        out_q: `~pulpcore.plugin.stages.DeclarativeContent`

    Returns:
        The artifact_saver stage as a coroutine to be included in a pipeline.
    """
    while True:
        declarative_content = await in_q.get()
        if declarative_content is None:
            break
        for declarative_artifact in declarative_content.d_artifacts:
            declarative_artifact.artifact.save()
        await out_q.put(declarative_content)
    await out_q.put(None)


async def query_existing_content_units(in_q, out_q):
    """
    Stages API stage replacing DeclarativeContent.content with already-saved Content objects.

    This stage expects `~pulpcore.plugin.stages.DeclarativeContent` units from `in_q` and inspects
    their associated `~pulpcore.plugin.stages.DeclarativeArtifact` objects. Each
    `DeclarativeArtifact` object stores one Artifact.

    This stage inspects any "unsaved" Content unit objects and searches for existing saved Content
    units inside Pulp with the same unit key. Any existing Content objects found replace their
    "unsaved" counterpart in the `~pulpcore.plugin.stages.DeclarativeContent` object.

    Each `~pulpcore.plugin.stages.DeclarativeContent` is sent to `out_q` after it has been handled.

    This stage drains all available items from `in_q` and batches everything into one large call to
    the db for efficiency.

    Args:
        in_q: `~pulpcore.plugin.stages.DeclarativeContent`
        out_q: `~pulpcore.plugin.stages.DeclarativeContent`

    Returns:
        The query_existing_content_units stage as a coroutine to be included in a pipeline.
    """
    declarative_content_list = []
    shutdown = False
    while True:
        try:
            content = in_q.get_nowait()
        except asyncio.QueueEmpty:
            if not declarative_content_list:
                content = await in_q.get()
                declarative_content_list.append(content)
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
                for declarative_content in declarative_content_list:
                    if declarative_content is None:
                        continue
                    not_same_unit = False
                    for field in result.natural_key_fields():
                        if getattr(declarative_content.content, field) != getattr(result, field):
                            not_same_unit = True
                            break
                    if not_same_unit:
                        continue
                    declarative_content.content = result
        for declarative_content in declarative_content_list:
            await out_q.put(declarative_content)
        declarative_content_list = []
        if shutdown:
            break
    await out_q.put(None)


async def content_unit_saver(in_q, out_q):
    """
    Stages API stage that saves DeclarativeContent.content objects and saves helper objects too.

    This stage expects `~pulpcore.plugin.stages.DeclarativeContent` units from `in_q` and inspects
    their associated `~pulpcore.plugin.stages.DeclarativeArtifact` objects. Each
    `DeclarativeArtifact` object stores one Artifact.

    Each "unsaved" Content objects is saved and a RemoteArtifact and ContentArtifact are created for
    it and saved also. This allows Pulp to refetch the Artifact in the future if the local copy is
    removed.

    Each `~pulpcore.plugin.stages.DeclarativeContent` is sent to after it has been handled.

    This stage drains all available items from `in_q` and batches everything into one large call to
    the db for efficiency.

    Args:
        in_q: `~pulpcore.plugin.stages.DeclarativeContent`
        out_q: `~pulpcore.plugin.models.Content`

    Returns:
        The content_unit_saver stage as a coroutine to be included in a pipeline.
    """
    declarative_content_list = []
    shutdown = False
    while True:
        try:
            declarative_content = in_q.get_nowait()
        except asyncio.QueueEmpty:
            if not declarative_content_list and not shutdown:
                declarative_content = await in_q.get()
                declarative_content_list.append(declarative_content)
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
                with transaction.atomic():
                    declarative_content.content.save()
                    for declarative_artifact in declarative_content.d_artifacts:
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

    This stage stores all content unit types and unit keys in memory before running for two reasons:

    1. To compute the units already associated but not received from `in_q`. These units are passed
       via `out_q` to the next stage as a `~django.db.models.query.QuerySet`.
    2. Units already associated will not be re-added. It would be ok, but it's not efficient.

    in_q data type: A saved `~pulpcore.plugin.models.Content` or subclass to be associated
    out_q data type: A `django.db.models.query.QuerySet` of `~pulpcore.plugin.models.Content` or
        subclass that are already associated but not included in the stream of items from `in_q`.
        One `django.db.models.query.QuerySet` is put for each `~pulpcore.plugin.models.Content`
        type.

    Args:
        new_version (RepositoryVersion): The RespositoryVersion this stage associates content with.

    Returns:
        A configured content_unit_association stage to be included in a pipeline.
    """
    version = new_version
    unit_keys_by_type = defaultdict(set)
    for unit in new_version.content.all():
        unit = unit.cast()
        unit_keys_by_type[type(unit)].add(unit.natural_key())
    async def actual_stage(in_q, out_q):
        """For each Content Unit associate it with the repository version"""
        with ProgressBar(message='Associating Content') as pb:
            while True:
                content = await in_q.get()
                if content is None:
                    break
                try:
                    unit_keys_by_type[type(content)].remove(content.natural_key())
                except KeyError:
                    version.add_content(content)
                    pb.increment()
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


def content_unit_unassociation(new_version):
    """
    A factory returning a Stages API stage that unassociates content units from `new_version`.

    in_q data type: `django.db.models.query.QuerySet` of `~pulpcore.plugin.models.Content` or
        subclass to be unassociated from `new_version`.
    out_q data type: `django.db.models.query.QuerySet` of `~pulpcore.plugin.models.Content` or
        subclass that were unassociated from `new_version`.

    Args:
        new_version (RepositoryVersion): The RespositoryVersion this stage unassociates content from

    Returns:
        The configured content_unit_unassociation stage to be included in a pipeline.
    """
    version = new_version
    async def actual_stage(in_q, out_q):
        """For each Content Unit from in_q, unassociate it with the repository version"""
        with ProgressBar(message='Un-Associating Content') as pb:
            while True:
                queryset_to_unassociate = await in_q.get()
                if queryset_to_unassociate is None:
                    break

                for unit in queryset_to_unassociate:
                    version.remove_content(unit)
                    pb.increment()

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
        >>>         dc = DeclarativeContent(content=unit, d_artifacts=[da])
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
                    stages.extend([content_unit_unassociation(new_version), end_stage])
                pipeline = create_pipeline(stages, self.in_q)
                loop.run_until_complete(pipeline)
