import web

from pulp.server.managers import factory as managers_factory
from pulp.server.webservices import serialization
from pulp.server.webservices.controllers.search import SearchController


class ConsumerGroupSearch(SearchController):
    def __init__(self):
        super(ConsumerGroupSearch, self).__init__(
            managers_factory.consumer_group_query_manager().find_by_criteria)

    # seems like the auth_required misses here. need to fix that in django
    def GET(self):
        items = self._get_query_results_from_get()
        for item in items:
            item.update(serialization.link.search_safe_link_obj(item['id']))
        return self.ok(items)

    def POST(self):
        items = self._get_query_results_from_post()
        for item in items:
            item.update(serialization.link.search_safe_link_obj(item['id']))
        return self.ok(items)
_URLS = (
    '/search/$', ConsumerGroupSearch  # resource search
)

application = web.application(_URLS, globals())
