import asyncio
from collections import defaultdict

from django.db import transaction
from django.db.models import Q

from pulpcore.plugin.models import ContentArtifact, RemoteArtifact


async def query_existing_content_units(in_q, out_q):
    """
    Stages API stage that saves :attr:`DeclarativeContent.content` objects and saves its related
    :class:`~pulpcore.plugin.models.ContentArtifact` and
    :class:`~pulpcore.plugin.models.RemoteArtifact` objects too.

    This stage expects :class:`~pulpcore.plugin.stages.DeclarativeContent` units from `in_q` and
    inspects their associated :class:`~pulpcore.plugin.stages.DeclarativeArtifact` objects. Each
    :class:`~pulpcore.plugin.stages.DeclarativeArtifact` object stores one
    :class:`~pulpcore.plugin.models.Artifact`.

    This stage inspects any "unsaved" Content unit objects and searches for existing saved Content
    units inside Pulp with the same unit key. Any existing Content objects found, replace their
    "unsaved" counterpart in the :class:`~pulpcore.plugin.stages.DeclarativeContent` object.

    Each :class:`~pulpcore.plugin.stages.DeclarativeContent` is sent to `out_q` after it has been
    handled.

    This stage drains all available items from `in_q` and batches everything into one large call to
    the db for efficiency.

    Args:
        in_q (:class:`asyncio.Queue`): Each item is a
            :class:`~pulpcore.plugin.stages.DeclarativeContent`
        out_q (:class:`asyncio.Queue`): Each item is a
            :class:`~pulpcore.plugin.stages.DeclarativeContent`

    Returns:
        The query_existing_content_units stage as a coroutine to be included in a pipeline.
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

        content_q_by_type = defaultdict(lambda: Q(pk=None))
        for declarative_content in batch:
            if declarative_content is None:
                shutdown = True
                continue

            model_type = type(declarative_content.content)
            unit_key = declarative_content.content.natural_key_dict()
            content_q_by_type[model_type] = content_q_by_type[model_type] | Q(**unit_key)

        for model_type in content_q_by_type.keys():
            for result in model_type.objects.filter(content_q_by_type[model_type]):
                for declarative_content in batch:
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
        for declarative_content in batch:
            await out_q.put(declarative_content)
        batch = []
        if shutdown:
            break
    await out_q.put(None)


async def content_unit_saver(in_q, out_q):
    """
    Stages API stage that saves :attr:`DeclarativeContent.content` objects and saves its related
    :class:`~pulpcore.plugin.models.ContentArtifact` and
    :class:`~pulpcore.plugin.models.RemoteArtifact` objects too.

    This stage expects :class:`~pulpcore.plugin.stages.DeclarativeContent` units from `in_q` and
    inspects their associated :class:`~pulpcore.plugin.stages.DeclarativeArtifact` objects. Each
    :class:`~pulpcore.plugin.stages.DeclarativeArtifact` object stores one
    :class:`~pulpcore.plugin.models.Artifact`.

    Each "unsaved" Content objects is saved and a :class:`~pulpcore.plugin.models.ContentArtifact`
    and :class:`~pulpcore.plugin.models.RemoteArtifact` objects too. This allows Pulp to refetch the
    Artifact in the future if the local copy is removed.

    Each :class:`~pulpcore.plugin.stages.DeclarativeContent` is sent to after it has been handled.

    This stage drains all available items from `in_q` and batches everything into one large call to
    the db for efficiency.

    Args:
        in_q (:class:`asyncio.Queue`): Each item is a
            :class:`~pulpcore.plugin.stages.DeclarativeContent`
        out_q (:class:`asyncio.Queue`): Each item is a
            :class:`~pulpcore.plugin.stages.DeclarativeContent`

    Returns:
        The content_unit_saver stage as a coroutine to be included in a pipeline.
    """
    batch = []
    shutdown = False
    while True:
        try:
            declarative_content = in_q.get_nowait()
        except asyncio.QueueEmpty:
            if not batch and not shutdown:
                declarative_content = await in_q.get()
                batch.append(declarative_content)
                continue
        else:
            batch.append(declarative_content)
            continue

        content_artifact_bulk = []
        remote_artifact_bulk = []
        remote_artifact_map = {}

        with transaction.atomic():
            for declarative_content in batch:
                if declarative_content is None:
                    shutdown = True
                    continue
                if declarative_content.content.pk is None:
                        declarative_content.content.save()
                        for declarative_artifact in declarative_content.d_artifacts:
                            content_artifact = ContentArtifact(
                                content=declarative_content.content,
                                artifact=declarative_artifact.artifact,
                                relative_path=declarative_artifact.relative_path
                            )
                            content_artifact_bulk.append(content_artifact)
                            remote_artifact_data = {
                                'url': declarative_artifact.url,
                                'size': declarative_artifact.artifact.size,
                                'md5': declarative_artifact.artifact.md5,
                                'sha1': declarative_artifact.artifact.sha1,
                                'sha224': declarative_artifact.artifact.sha224,
                                'sha256': declarative_artifact.artifact.sha256,
                                'sha384': declarative_artifact.artifact.sha384,
                                'sha512': declarative_artifact.artifact.sha512,
                                'remote': declarative_artifact.remote,
                            }
                            rel_path = content_artifact.relative_path
                            remote_artifact_map[rel_path] = remote_artifact_data

            for content_artifact in ContentArtifact.objects.bulk_create(content_artifact_bulk):
                remote_artifact_data = remote_artifact_map.pop(content_artifact.relative_path)
                new_remote_artifact = RemoteArtifact(
                    content_artifact=content_artifact, **remote_artifact_data
                )
                remote_artifact_bulk.append(new_remote_artifact)

            RemoteArtifact.objects.bulk_create(remote_artifact_bulk)

        for declarative_content in batch:
            if declarative_content is None:
                continue
            await out_q.put(declarative_content)
        if shutdown:
            break
        batch = []
    await out_q.put(None)
