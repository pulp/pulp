import asyncio
import os
import shutil

from django.db.models import Q

from pulpcore.plugin.models import Artifact, ProgressBar


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
            if content is None:
                continue
            await out_q.put(content)
        declarative_content = []
        if shutdown:
            break
    await out_q.put(None)


class artifact_downloader:
    """
    An object containing a Stages API stage to download missing Artifacts, but don't call save()

    The actual stage is the `stage` attribute which can be used as follows:

    >>> artifact_downloader(max_concurrent_downloads=42).stage  # This is the real stage

    in_q data type: A `~pulpcore.plugin.stages.DeclarativeContent` with potentially files missing
        `~pulpcore.plugin.stages.DeclarativeArtifact.artifact` objects.
    out_q data type: A `~pulpcore.plugin.stages.DeclarativeContent` with all files downloaded for
        all `~pulpcore.plugin.stages.DeclarativeArtifact.artifact` objects.

    This stage downloads the file for any Artifact objects missing files and creates a new Artifact
    from the downloaded file and its digest data. The new Artifact is *not* saved but added to the
    `~pulpcore.plugin.stages.DeclarativeArtifact` object, replacing the likely incomplete Artifact.

    Each `~pulpcore.plugin.stages.DeclarativeContent` is sent to `out_q` after all of its
    `~pulpcore.plugin.stages.DeclarativeArtifact` objects have been handled.

    This stage creates a ProgressBar named 'Downloading Artifacts' that counts the number of
    downloads completed. Since it's a stream the total count isn't known until it's finished.

    This stage drains all available items from `in_q` and starts as many downloaders as possible.

    Args:
        max_concurrent_downloads (int): The maximum number of concurrent downloads this stage will
            run. Default is 100.

    Returns:
        An object containing the artifact_downloader stage to be included in a pipeline.
    """

    def __init__(self, max_concurrent_downloads=100):
        self.max_concurrent_downloads = max_concurrent_downloads

    async def stage(self, in_q, out_q):
        """Download undownloaded Artifacts, but don't save them"""
        pending = set()
        incoming_content = []
        outstanding_downloads = 0
        shutdown = False
        saturated = False
        with ProgressBar(message='Downloading Artifacts') as pb:
            while True:
                if not saturated:
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

                for i, content in enumerate(incoming_content):
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
                    outstanding_downloads = outstanding_downloads + len(downloaders_for_content)
                    downloaders_for_content.append(return_content_for_downloader(content))
                    pending.add(asyncio.gather(*downloaders_for_content))
                    if outstanding_downloads > self.max_concurrent_downloads:
                        saturated = True
                        incoming_content = incoming_content[i + 1:]  # remove handled content
                        break
                else:
                    incoming_content = []

                if pending:
                    done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                    for gathered_downloaders in done:
                        results = gathered_downloaders.result()
                        for download_result in results[:-1]:
                            content = results[-1]
                            for declarative_artifact in content.d_artifacts:
                                if declarative_artifact.artifact._state.adding:
                                    new_artifact = Artifact(
                                        **download_result.artifact_attributes,
                                        file=download_result.path
                                    )
                                    declarative_artifact.artifact = new_artifact
                            pb.done = pb.done + len(content.d_artifacts)
                            outstanding_downloads = outstanding_downloads - len(content.d_artifacts)
                            await out_q.put(content)
                else:
                    if shutdown:
                        break

                if outstanding_downloads < self.max_concurrent_downloads:
                    saturated = False
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

    Args:
        in_q: `~pulpcore.plugin.stages.DeclarativeContent`
        out_q: `~pulpcore.plugin.stages.DeclarativeContent`

    Returns:
        The artifact_saver stage as a coroutine to be included in a pipeline.
    """
    shutdown = False
    declarative_content_list = []
    while not shutdown:
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

        artifacts_to_save = []
        for declarative_content in declarative_content_list:
            if declarative_content is None:
                shutdown = True
                break
            for declarative_artifact in declarative_content.d_artifacts:
                if declarative_artifact.artifact._state.adding:
                    src_path = str(declarative_artifact.artifact.file)
                    dst_path = declarative_artifact.artifact.storage_path(None)
                    try:
                        shutil.move(src_path, dst_path)
                    except FileNotFoundError:
                        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                        shutil.move(src_path, dst_path)
                    declarative_artifact.artifact.file = dst_path
                    artifacts_to_save.append(declarative_artifact.artifact)

        if artifacts_to_save:
            Artifact.objects.bulk_create(artifacts_to_save)

        for declarative_content in declarative_content_list:
            if declarative_content is None:
                continue
            await out_q.put(declarative_content)

        declarative_content_list = []

    await out_q.put(None)
