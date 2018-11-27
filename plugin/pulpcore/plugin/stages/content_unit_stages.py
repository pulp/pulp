from collections import defaultdict

from django.db import IntegrityError, transaction
from django.db.models import Q

from pulpcore.plugin.models import ContentArtifact, RemoteArtifact

from .api import Stage


class QueryExistingContentUnits(Stage):
    """
    A Stages API stage that saves :attr:`DeclarativeContent.content` objects and saves its related
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
            content_q_by_type = defaultdict(lambda: Q(pk=None))
            for declarative_content in batch:
                model_type = type(declarative_content.content)
                unit_q = declarative_content.content.q()
                content_q_by_type[model_type] = content_q_by_type[model_type] | unit_q

            for model_type in content_q_by_type.keys():
                for result in model_type.objects.filter(content_q_by_type[model_type]):
                    for declarative_content in batch:
                        if type(declarative_content.content) is not model_type:
                            continue
                        not_same_unit = False
                        for field in result.natural_key_fields():
                            in_memory_digest_value = getattr(declarative_content.content, field)
                            if in_memory_digest_value != getattr(result, field):
                                not_same_unit = True
                                break
                        if not_same_unit:
                            continue
                        declarative_content.content = result
            for declarative_content in batch:
                await out_q.put(declarative_content)
        await out_q.put(None)


class ContentUnitSaver(Stage):
    """
    A Stages API stage that saves :attr:`DeclarativeContent.content` objects and saves its related
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
            content_artifact_bulk = []
            remote_artifact_bulk = []
            remote_artifact_map = {}

            with transaction.atomic():
                await self._pre_save(batch)
                for declarative_content in batch:
                    if declarative_content.content.pk is None:
                        try:
                            with transaction.atomic():
                                declarative_content.content.save()
                        except IntegrityError:
                            declarative_content.content = \
                                declarative_content.content.__class__.objects.get(
                                    declarative_content.content.q())
                            continue
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
                            rel_path = declarative_artifact.relative_path
                            content_key = str(content_artifact.content.pk) + rel_path
                            remote_artifact_map[content_key] = remote_artifact_data

                for content_artifact in ContentArtifact.objects.bulk_get_or_create(
                        content_artifact_bulk):
                    rel_path = content_artifact.relative_path
                    content_key = str(content_artifact.content.pk) + rel_path
                    remote_artifact_data = remote_artifact_map.pop(content_key)
                    new_remote_artifact = RemoteArtifact(
                        content_artifact=content_artifact, **remote_artifact_data
                    )
                    remote_artifact_bulk.append(new_remote_artifact)

                RemoteArtifact.objects.bulk_get_or_create(remote_artifact_bulk)
                await self._post_save(batch)

            for declarative_content in batch:
                await out_q.put(declarative_content)
        await out_q.put(None)

    async def _pre_save(self, batch):
        """
        A hook plugin-writers can override to save related objects prior to content unit saving.

        This is run within the same transaction as the content unit saving.

        Args:
            batch (list of :class:`~pulpcore.plugin.stages.DeclarativeContent`): The batch of
                :class:`~pulpcore.plugin.stages.DeclarativeContent` objects to be saved.

        """
        pass

    async def _post_save(self, batch):
        """
        A hook plugin-writers can override to save related objects after content unit saving.

        This is run within the same transaction as the content unit saving.

        Args:
            batch (list of :class:`~pulpcore.plugin.stages.DeclarativeContent`): The batch of
                :class:`~pulpcore.plugin.stages.DeclarativeContent` objects to be saved.

        """
        pass
