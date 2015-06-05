import logging

from pulp.common import dateutils
from pulp.plugins.loader import api as plugin_api
from pulp.server.db import connection, model

_logger = logging.getLogger(__name__)


def find_repo_content_units(
        repository, repo_content_unit_q=None,
        units_q=None, units_fields=None, limit=None, skip=None):
    """
    Search content units associated with a given repository

    Each association returned will have a parameter "unit" set to the actual unit

    :param repository: The repository to search.
    :type repository: pulp.server.db.model.Repository
    :param repo_content_unit_q: Any query filters to apply to the RepoContentUnits.
    :type repo_content_unit_q: mongoengine.Q
    :param units_q: Any query filters to apply to the ContentUnits.
    :type units_q: mongoengine.Q
    :param units_fields: List of fields to fetch for the unit objects, defaults to all fields
    :type units_fields: List of str
    :param limit: The maximum number of items to return for the given query.
    :type limit: int
    :param skip: The starting offset.
    :type skip: int
    :return: Content unit assoociations matching the query.
    :rtype: generator of pulp.server.db.model.ContentUnit
    """

    qs = model.RepositoryContentUnit.objects(q_obj=repo_content_unit_q,
                                             repo_id=repository.repo_id)

    type_map = {}
    content_units = {}

    yield_count = 1
    skip_count = 0

    for repo_content_unit in qs:
        id_set = type_map.setdefault(repo_content_unit.unit_type_id, set())
        id_set.add(repo_content_unit.unit_id)
        content_unit_set = content_units.setdefault(repo_content_unit.unit_type_id, dict())
        content_unit_set[repo_content_unit.unit_id] = repo_content_unit

    for unit_type, unit_ids in type_map.iteritems():
        qs = plugin_api.get_unit_model_by_id(unit_type).objects(
            q_obj=units_q, __raw__={'_id': {'$in': list(unit_ids)}})
        if units_fields:
            qs = qs.only(units_fields)

        for unit in qs:
            if skip and skip_count < skip:
                skip_count += 1
                continue
            cu = content_units[unit_type][unit.id]
            cu.unit = unit
            yield cu

            if limit:
                if yield_count >= limit:
                    return

            yield_count += 1


def rebuild_content_unit_counts(repository):
    """
    Update the content_unit_counts field on a Repository.

    :param repository: The repository to update
    :type repository: pulp.server.db.model.Repository
    """
    db = connection.get_database()

    pipeline = [
        {'$match': {'repo_id': repository.repo_id}},
        {'$group': {'_id': '$unit_type_id', 'sum': {'$sum': 1}}}]
    q = db.command('aggregate', 'repo_content_units', pipeline=pipeline)

    # Flip this into the form that we need
    counts = {}
    for result in q['result']:
        counts[result['_id']] = result['sum']

    # Use the raw query since there is currently a conflict with the id and the repo_id fields
    model.Repository.objects(__raw__={'id': repository.repo_id}).update_one(
        set__content_unit_counts=counts)


def associate_single_unit(repository, unit):
    """
    Associate a single unit to a repository
    :param repository: The repository to update
    :type repository: pulp.server.db.model.Repository
    :param unit: The unit to associate to the repository
    :type unit: pulp.server.db.model.ContentUnit
    """
    current_timestamp = dateutils.now_utc_timestamp()
    formatted_datetime = dateutils.format_iso8601_utc_timestamp(current_timestamp)
    qs = model.RepositoryContentUnit.objects(
        repo_id=repository.repo_id,
        unit_id=unit.id,
        unit_type_id=unit.unit_type_id)
    qs.update_one(
        set_on_insert__created=formatted_datetime,
        set__updated=formatted_datetime,
        upsert=True)
