from pulp.server.db.connection import get_collection


def migrate(*args, **kwargs):
    """
    Remove last_updated and last_override_config from the importer collection.
    Migration 0025 added them, but was released sooner than it should have
    been. For details, see https://pulp.plan.io/issues/2378
    """

    collection = get_collection('repo_importers')

    collection.update({}, {'$unset': {'last_updated': 1}}, multi=True)
    collection.update({}, {'$unset': {'last_override_config': 1}}, multi=True)

