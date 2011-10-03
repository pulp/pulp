
"""
Repo module containing repo quries based on HTTP query parameters.
"""

from pulp.server.db.model.resource import Repo
from pulp.server.webservices import http
from pulp.server.webservices.queries.common import OPERATION_FILTERS


def collection():
    valid_filters = []
    valid_filters.extend(OPERATION_FILTERS)
    query_params = http.query_parameters(valid_filters)
    db_collection = Repo.get_collection()
    spec = {}
    fields = []
    db_cursor = db_collection.find(spec, fields=fields or None)


def resource(repo_id):
    valid_filters = ['field']
    query_param = http.query_parameters(valid_filters)
    fields = query_param.get('field', None)
    db_collection = Repo.get_collection()
    repo = db_collection.find_one({'_id': repo_id}, fields=fields)
    return repo


def subcollection_packages(repo_id):
    pass
