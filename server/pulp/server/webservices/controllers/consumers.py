"""
This module contains the consumer related web controllers.
"""
import web

from pulp.server.db.model.criteria import Criteria
from pulp.server.webservices import serialization
from pulp.server.webservices.controllers.search import SearchController
import pulp.server.managers.factory as managers


def expand_consumers(options, consumers):
    """
    Expand a list of users based on flags specified in the
    post body or query parameters.  The _href is always added by the
    serialization function used.
    Supported options:
      details - synonym for: (bindings=True,)
      bindings - include bindings
    @param options: The (expanding) options.
    @type options: dict
    @param consumers: A list of consumers
    @type consumers: list
    @return: A list of expanded consumers.
    @rtype: list
    """
    if options.get('details', False):
        options['bindings'] = True
    # add bindings
    if options.get('bindings', False):
        ids = [c['id'] for c in consumers]
        manager = managers.consumer_bind_manager()
        criteria = Criteria({'consumer_id': {'$in': ids}})
        bindings = manager.find_by_criteria(criteria)
        collated = {}
        for b in bindings:
            lst = collated.setdefault(b['consumer_id'], [])
            lst.append(b)
        for _consumer in consumers:
            _consumer['bindings'] = \
                [serialization.binding.serialize(b, False)
                    for b in collated.get(_consumer['id'], [])]
    return consumers


class ConsumerSearch(SearchController):

    def __init__(self):
        super(ConsumerSearch, self).__init__(
            managers.consumer_query_manager().find_by_criteria)

    def GET(self):
        params = web.input()
        ignored = ('details', 'bindings')
        found = self._get_query_results_from_get(ignored)
        consumers = expand_consumers(params, found)
        for c in consumers:
            href = serialization.link.search_safe_link_obj(c['id'])
            c.update(href)
        return self.ok(consumers)

    def POST(self):
        body = self.params()
        found = self._get_query_results_from_post()
        consumers = expand_consumers(body, found)
        for c in consumers:
            href = serialization.link.search_safe_link_obj(c['id'])
            c.update(href)
        return self.ok(consumers)


class BindingSearch(SearchController):
    """
    Bind search.
    """
    def __init__(self):
        SearchController.__init__(self, managers.consumer_bind_manager().find_by_criteria)


class ProfileSearch(SearchController):
    """
    Profile search.
    """
    def __init__(self):
        SearchController.__init__(self, managers.consumer_profile_manager().find_by_criteria)

# -- web.py application -------------------------------------------------------

urls = (
    '/binding/search/$', BindingSearch,
    '/profile/search/$', ProfileSearch,
    '/search/$', ConsumerSearch,
)

application = web.application(urls, globals())
