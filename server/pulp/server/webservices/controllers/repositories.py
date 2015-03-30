"""
This module contains the web controllers for Repositories.
"""
import logging
import sys

import web

from pulp.common import dateutils
from pulp.server.auth.authorization import READ
from pulp.server.db.model.criteria import UnitAssociationCriteria
from pulp.server.webservices import serialization
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required
from pulp.server.webservices.controllers.search import SearchController
import pulp.server.exceptions as exceptions
import pulp.server.managers.factory as manager_factory


_logger = logging.getLogger(__name__)


def _merge_related_objects(name, manager, repos):
    """
    Takes a list of Repo objects and adds their corresponding related objects
    in a list under the attribute given in 'name'. Uses the given manager to
    access the related objects by passing the list of IDs for the given repos.
    This is most commonly used for RepoImporter or RepoDistributor objects in
    lists under the 'importers' and 'distributors' attributes.

    @param name: name of the field, such as 'importers' or 'distributors'.
    @type  name: str

    @param manager: manager class for the object type. must implement a method
                    'find_by_repo_list' that takes a list of repo ids.

    @param repos: list of Repo instances that should have importers and
                  distributors added.
    @type  repos  list of Repo instances

    @return the same list that was passed in, just for convenience. The list
            itself is not modified- only its members are modified in-place.
    @rtype  list of Repo instances
    """
    repo_ids = tuple(repo['id'] for repo in repos)

    # make it cheap to access each repo by id
    repo_dict = dict((repo['id'], repo) for repo in repos)

    # guarantee that at least an empty list will be present
    for repo in repos:
        repo[name] = []

    for item in manager.find_by_repo_list(repo_ids):
        repo_dict[item['repo_id']][name].append(item)

    return repos


def _convert_repo_dates_to_strings(repo):
    """
    Convert the last_unit_added & last_unit_removed fields of a repository
    This modifies the repository in place

    :param repo:  diatabase representation of a repo
    :type repo: dict
    """
    # convert the native datetime object to a string with timezone specified
    last_unit_added = repo.get('last_unit_added')
    if last_unit_added:
        new_date = dateutils.to_utc_datetime(last_unit_added,
                                             no_tz_equals_local_tz=False)
        repo['last_unit_added'] = dateutils.format_iso8601_datetime(new_date)
    last_unit_removed = repo.get('last_unit_removed')
    if last_unit_removed:
        new_date = dateutils.to_utc_datetime(last_unit_removed,
                                             no_tz_equals_local_tz=False)
        repo['last_unit_removed'] = dateutils.format_iso8601_datetime(new_date)


class RepoCollection(JSONController):

    # Scope: Collection
    # GET:   Retrieve all repositories in the system
    # POST:  Repository Create

    @staticmethod
    def _process_repos(repos, importers=False, distributors=False):
        """
        Apply standard processing to a collection of repositories being returned
        to a client. Adds the object link and optionally adds related importers
        and distributors.

        @param repos: collection of repositories
        @type  repos: list, tuple

        @param importers:   iff True, adds related importers under the
                            attribute "importers".
        @type  importers:   bool

        @param distributors:    iff True, adds related distributors under the
                                attribute "distributors".
        @type  distributors:    bool

        @return the same list that was passed in, just for convenience. The list
                itself is not modified- only its members are modified in-place.
        @rtype  list of Repo instances
        """
        if importers:
            _merge_related_objects(
                'importers', manager_factory.repo_importer_manager(), repos)
        if distributors:
            _merge_related_objects(
                'distributors', manager_factory.repo_distributor_manager(), repos)

        for repo in repos:
            repo.update(serialization.link.search_safe_link_obj(repo['id']))
            _convert_repo_dates_to_strings(repo)

            # Remove internally used scratchpad from repo details
            if 'scratchpad' in repo:
                del repo['scratchpad']

        return repos


class RepoSearch(SearchController):
    def __init__(self):
        super(RepoSearch, self).__init__(
            manager_factory.repo_query_manager().find_by_criteria)

    @auth_required(READ)
    def GET(self):
        query_params = web.input()
        if query_params.pop('details', False):
            query_params['importers'] = True
            query_params['distributors'] = True
        items = self._get_query_results_from_get(
            ('details', 'importers', 'distributors'))

        RepoCollection._process_repos(
            items,
            query_params.pop('importers', False),
            query_params.pop('distributors', False)
        )
        return self.ok(items)

    @auth_required(READ)
    def POST(self):
        """
        Searches based on a Criteria object. Requires a posted parameter
        'criteria' which has a data structure that can be turned into a
        Criteria instance.
        """
        items = self._get_query_results_from_post()

        RepoCollection._process_repos(
            items,
            self.params().get('importers', False),
            self.params().get('distributors', False)
        )
        return self.ok(items)


class RepoUnitAdvancedSearch(JSONController):

    # Scope: Search
    # POST:  Advanced search for repo unit associations

    @auth_required(READ)
    def POST(self, repo_id):
        # Params
        params = self.params()
        query = params.get('criteria', None)

        repo_query_manager = manager_factory.repo_query_manager()
        repo = repo_query_manager.find_by_id(repo_id)
        if repo is None:
            raise exceptions.MissingResource(repo_id=repo_id)

        if query is None:
            raise exceptions.MissingValue(['criteria'])

        try:
            criteria = UnitAssociationCriteria.from_client_input(query)
        except:
            _logger.error('Error parsing association criteria [%s]' % query)
            raise exceptions.PulpDataException(), None, sys.exc_info()[2]

        # Data lookup
        manager = manager_factory.repo_unit_association_query_manager()
        if criteria.type_ids is not None and len(criteria.type_ids) == 1:
            type_id = criteria.type_ids[0]
            units = manager.get_units_by_type(repo_id, type_id, criteria=criteria)
        else:
            units = manager.get_units_across_types(repo_id, criteria=criteria)

        return self.ok(units)

# These are defined under /v2/repositories/ (see application.py to double-check)
urls = (
    '/search/$', 'RepoSearch',  # resource search
    '/([^/]+)/search/units/$', 'RepoUnitAdvancedSearch',  # resource search
)

application = web.application(urls, globals())
