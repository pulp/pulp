import web

from pulp.server.auth import authorization
from pulp.server.managers import factory as managers_factory
from pulp.server.webservices import serialization
from pulp.server.webservices.controllers.decorators import auth_required
from pulp.server.webservices.controllers.search import SearchController


class RepoGroupSearch(SearchController):
    def __init__(self):
        super(RepoGroupSearch, self).__init__(
            managers_factory.repo_group_query_manager().find_by_criteria)

    @auth_required(authorization.READ)
    def GET(self):
        items = self._get_query_results_from_get()
        for item in items:
            item.update(serialization.link.search_safe_link_obj(item['id']))
        return self.ok(items)

    @auth_required(authorization.READ)
    def POST(self):
        items = self._get_query_results_from_post()
        for item in items:
            item.update(serialization.link.search_safe_link_obj(item['id']))
        return self.ok(items)


_URLS = ('/search/$', RepoGroupSearch)

application = web.application(_URLS, globals())
