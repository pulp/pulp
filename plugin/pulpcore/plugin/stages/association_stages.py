from collections import defaultdict

from django.db.models import Q

from pulpcore.plugin.models import ProgressBar

from .api import Stage


class ContentUnitAssociation(Stage):
    """
    A Stages API stage that associates content units with `new_version`.

    This stage stores all content unit types and unit keys in memory before running. This is done to
    compute the units already associated but not received from `in_q`. These units are passed via
    `out_q` to the next stage as a :class:`django.db.models.query.QuerySet`.

    This stage creates a ProgressBar named 'Associating Content' that counts the number of units
    associated. Since it's a stream the total count isn't known until it's finished.

    Args:
        new_version (:class:`~pulpcore.plugin.models.RepositoryVersion`): The repo version this
            stage associates content with.
        args: unused positional arguments passed along to :class:`~pulpcore.plugin.stages.Stage`.
        kwargs: unused keyword arguments passed along to :class:`~pulpcore.plugin.stages.Stage`.
    """

    def __init__(self, new_version, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.new_version = new_version
        self.unit_keys_by_type = defaultdict(set)
        for unit in self.new_version.content.all():
            unit = unit.cast()
            self.unit_keys_by_type[type(unit)].add(unit.natural_key())

    async def __call__(self, in_q, out_q):
        """
        The coroutine for this stage.

        Args:
            in_q (:class:`asyncio.Queue`): Each item is a
                :class:`~pulpcore.plugin.stages.DeclarativeContent` with saved `content` that needs
                to be associated.
            out_q (:class:`asyncio.Queue`): Each item is a :class:`django.db.models.query.QuerySet`
                of :class:`~pulpcore.plugin.models.Content` subclass that are already associated but
                not included in the stream of items from `in_q`. One
                :class:`django.db.models.query.QuerySet` is put for each
                :class:`~pulpcore.plugin.models.Content` type.

        Returns:
            The coroutine for this stage.
        """
        with ProgressBar(message='Associating Content') as pb:
            async for batch in self.batches(in_q):
                content_q_by_type = defaultdict(lambda: Q(pk=None))
                for declarative_content in batch:
                    try:
                        unit_key = declarative_content.content.natural_key()
                        self.unit_keys_by_type[type(declarative_content.content)].remove(unit_key)
                    except KeyError:
                        model_type = type(declarative_content.content)
                        unit_key_dict = declarative_content.content.natural_key_dict()
                        unit_q = Q(**unit_key_dict)
                        content_q_by_type[model_type] = content_q_by_type[model_type] | unit_q

                for model_type, q_object in content_q_by_type.items():
                    queryset = model_type.objects.filter(q_object)
                    self.new_version.add_content(queryset)
                    pb.done = pb.done + queryset.count()
                    pb.save()

            for unit_type, ids in self.unit_keys_by_type.items():
                if ids:
                    units_to_unassociate = Q()
                    for unit_key in self.unit_keys_by_type[unit_type]:
                        query_dict = {}
                        for i, key_name in enumerate(unit_type.natural_key_fields()):
                            query_dict[key_name] = unit_key[i]
                        units_to_unassociate |= Q(**query_dict)
                    await out_q.put(unit_type.objects.filter(units_to_unassociate))
            await out_q.put(None)


class ContentUnitUnassociation(Stage):
    """
    A Stages API stage that unassociates content units from `new_version`.

    This stage creates a ProgressBar named 'Un-Associating Content' that counts the number of units
    un-associated. Since it's a stream the total count isn't known until it's finished.

    Args:
        new_version (:class:`~pulpcore.plugin.models.RepositoryVersion`): The repo version this
            stage unassociates content from.
        args: unused positional arguments passed along to :class:`~pulpcore.plugin.stages.Stage`.
        kwargs: unused keyword arguments passed along to :class:`~pulpcore.plugin.stages.Stage`.
    """

    def __init__(self, new_version, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.new_version = new_version

    async def __call__(self, in_q, out_q):
            """
            The coroutine for this stage.

            Args:
                in_q (:class:`asyncio.Queue`): Each item is a
                    :class:`django.db.models.query.QuerySet` of
                    :class:`~pulpcore.plugin.models.Content` subclass that are already associated
                    but not included in the stream of items from `in_q`. One
                    :class:`django.db.models.query.QuerySet` is put for each
                    :class:`~pulpcore.plugin.models.Content` type.
                out_q (:class:`asyncio.Queue`): Each item is a
                    :class:`django.db.models.query.QuerySet` of
                    :class:`~pulpcore.plugin.models.Content` subclass that were unassociated. One
                    :class:`django.db.models.query.QuerySet` is put for each
                    :class:`~pulpcore.plugin.models.Content` type.

            Returns:
                The coroutine for this stage.
            """
            with ProgressBar(message='Un-Associating Content') as pb:
                while True:
                    queryset_to_unassociate = await in_q.get()
                    if queryset_to_unassociate is None:
                        break

                    self.new_version.remove_content(queryset_to_unassociate)
                    pb.done = pb.done + queryset_to_unassociate.count()
                    pb.save()

                    await out_q.put(queryset_to_unassociate)
                await out_q.put(None)
