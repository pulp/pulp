import asyncio

from django.core.files import File
from django.core.files.storage import DefaultStorage
from django.db.models import Q

from pulpcore.plugin.models import Artifact, ProgressBar

from .api import Stage


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
        batch = []
        shutdown = False
        while True:
            try:
                content = in_q.get_nowait()
            except asyncio.QueueEmpty:
                if not batch:
                    content = await in_q.get()
                    batch.append(content)
                    continue
            else:
                batch.append(content)
                continue

            all_artifacts_q = Q(pk=None)
            for content in batch:
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
                    if one_artifact_q:
                        all_artifacts_q |= one_artifact_q

            for artifact in Artifact.objects.filter(all_artifacts_q):
                for content in batch:
                    if content is None:
                        continue
                    for declarative_artifact in content.d_artifacts:
                        for digest_name in artifact.DIGEST_FIELDS:
                            digest_value = getattr(declarative_artifact.artifact, digest_name)
                            if digest_value and digest_value == getattr(artifact, digest_name):
                                declarative_artifact.artifact = artifact
                                break
            for content in batch:
                if content is None:
                    continue
                await out_q.put(content)
            batch = []
            if shutdown:
                break
        await out_q.put(None)


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

    This stage drains all available items from `in_q` and starts as many downloaders as possible.

    Args:
        max_concurrent_downloads (int): The maximum number of concurrent downloads this stage will
            run. Default is 100.
        args: unused positional arguments passed along to :class:`~pulpcore.plugin.stages.Stage`.
        kwargs: unused keyword arguments passed along to :class:`~pulpcore.plugin.stages.Stage`.
    """

    def __init__(self, max_concurrent_downloads=100, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_concurrent_downloads = max_concurrent_downloads

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
        pending = set()
        unhandled_content = []
        outstanding_downloads = 0
        shutdown = False
        saturated = False
        with ProgressBar(message='Downloading Artifacts') as pb:
            while True:
                if not saturated:
                    try:
                        content = in_q.get_nowait()
                    except asyncio.QueueEmpty:
                        if not unhandled_content and not shutdown and not pending:
                            content = await in_q.get()
                            unhandled_content.append(content)
                            continue
                    else:
                        unhandled_content.append(content)
                        continue

                for i, content in enumerate(unhandled_content):
                    if content is None:
                        shutdown = True
                        continue
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
                                declarative_artifact.url,
                                **validation_kwargs
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
                        unhandled_content = unhandled_content[i + 1:]  # remove handled content
                        break
                else:
                    unhandled_content = []

                if pending:
                    done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                    for gathered_downloaders in done:
                        one_units_downloads = gathered_downloaders.result()
                        content = one_units_downloads[-1]
                        for download_result in one_units_downloads[:-1]:
                            def url_lookup(x):
                                return x.url == download_result.url
                            d_artifact = list(filter(url_lookup, content.d_artifacts))[0]
                            if d_artifact.artifact.pk is None:
                                new_artifact = Artifact(
                                    **download_result.artifact_attributes,
                                    file=download_result.path
                                )
                                d_artifact.artifact = new_artifact
                                pb.done = pb.done + 1
                                pb.save()
                                outstanding_downloads = outstanding_downloads - 1
                        await out_q.put(content)
                else:
                    if shutdown:
                        break

                if outstanding_downloads < self.max_concurrent_downloads:
                    saturated = False
        await out_q.put(None)


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
        storage_backend = DefaultStorage()
        shutdown = False
        batch = []
        while not shutdown:
            try:
                content = in_q.get_nowait()
            except asyncio.QueueEmpty:
                if not batch:
                    content = await in_q.get()
                    batch.append(content)
                    continue
            else:
                batch.append(content)
                continue

            artifacts_to_save = []
            for declarative_content in batch:
                if declarative_content is None:
                    shutdown = True
                    break
                for declarative_artifact in declarative_content.d_artifacts:
                    if declarative_artifact.artifact.pk is None:
                        src_path = str(declarative_artifact.artifact.file)
                        dst_path = declarative_artifact.artifact.storage_path(None)
                        with open(src_path, mode='rb') as input_file:
                            django_file_obj = File(input_file)
                            storage_backend.save(dst_path, django_file_obj)
                        declarative_artifact.artifact.file = dst_path
                        artifacts_to_save.append(declarative_artifact.artifact)

            if artifacts_to_save:
                Artifact.objects.bulk_create(artifacts_to_save)

            for declarative_content in batch:
                if declarative_content is None:
                    continue
                await out_q.put(declarative_content)

            batch = []

        await out_q.put(None)
