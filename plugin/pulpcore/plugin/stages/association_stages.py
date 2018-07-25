import asyncio
from collections import defaultdict

from django.db.models import Q

from pulpcore.plugin.models import ProgressBar


class content_unit_association:
    """
    An object containing a Stages API stage that associates content units with `new_version`.

    The actual stage is the `stage` attribute which can be used as follows:

    >>> content_unit_association(my_new_version).stage  # This is the real stage

    This stage stores all content unit types and unit keys in memory before running. This is done to
    compute the units already associated but not received from `in_q`. These units are passed via
    `out_q` to the next stage as a `~django.db.models.query.QuerySet`.

    in_q data type: A `~pulpcore.plugin.stages.DeclarativeContent` with saved `content` that needs
        to be associated.
    out_q data type: A `django.db.models.query.QuerySet` of `~pulpcore.plugin.models.Content` or
        subclass that are already associated but not included in the stream of items from `in_q`.
        One `django.db.models.query.QuerySet` is put for each `~pulpcore.plugin.models.Content`
        type.

    This stage creates a ProgressBar named 'Associating Content' that counts the number of units
    associated. Since it's a stream the total count isn't known until it's finished.

    Args:
        new_version (pulpcore.plugin.models.RepositoryVersion): The repo version this stage
            associates content with.

    Returns:
        An object containing the content_unit_association stage to be included in a pipeline.
    """

    def __init__(self, new_version):
        self.new_version = new_version
        self.unit_keys_by_type = defaultdict(set)
        for unit in self.new_version.content.all():
            unit = unit.cast()
            self.unit_keys_by_type[type(unit)].add(unit.natural_key())

    async def stage(self, in_q, out_q):
        """For each Content Unit associate it with the repository version"""
        with ProgressBar(message='Associating Content') as pb:
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

                content_q_by_type = defaultdict(lambda: Q(pk=None))
                for declarative_content in declarative_content_list:
                    if declarative_content is None:
                        shutdown = True
                        continue
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

                if shutdown:
                    break
                declarative_content_list = []

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


class content_unit_unassociation:
    """
    An object containing a Stages API stage that unassociates content units from `new_version`.

    The actual stage is the `stage` attribute which can be used as follows:

    >>> content_unit_unassociation(my_new_version).stage  # This is the real stage

    in_q data type: `django.db.models.query.QuerySet` of `~pulpcore.plugin.models.Content` or
        subclass to be unassociated from `new_version`.
    out_q data type: `django.db.models.query.QuerySet` of `~pulpcore.plugin.models.Content` or
        subclass that were unassociated from `new_version`.

    This stage creates a ProgressBar named 'Un-Associating Content' that counts the number of units
    un-associated. Since it's a stream the total count isn't known until it's finished.

    Args:
        new_version (pulpcore.plugin.models.RepositoryVersion): The repo version this stage
            unassociates content from

    Returns:
        An object containing the configured content_unit_unassociation stage to be included in a
            pipeline.
    """

    def __init__(self, new_version):
        self.new_version = new_version

    async def stage(self, in_q, out_q):
            """For each Content Unit from in_q, unassociate it with the repository version"""
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
