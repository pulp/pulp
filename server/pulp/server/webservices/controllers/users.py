import web

from pulp.server.auth.authorization import READ
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required
from pulp.server.webservices.controllers.search import SearchController
from pulp.server.webservices import serialization
import pulp.server.managers.factory as managers


USER_WHITELIST = [u'login', u'name', u'roles']


class UserSearch(SearchController):
    @staticmethod
    def _process_users(users):
        """
        Apply standard processing to a collection of users being returned
        to a client.  Adds the object link and removes user password.

        @param users: collection of users
        @type  users: list, tuple

        @return the same list that was passed in, just for convenience. The list
                itself is not modified- only its members are modified in-place.
        @rtype  list of User instances
        """
        for user in users:
            user.update(serialization.link.search_safe_link_obj(user['login']))
            JSONController.process_dictionary_against_whitelist(user, USER_WHITELIST)
        return users

    def __init__(self):
        super(UserSearch, self).__init__(
            managers.user_query_manager().find_by_criteria)

    @auth_required(READ)
    def GET(self):
        users = self._get_query_results_from_get(is_user_search=True)
        self._process_users(users)

        return self.ok(users)

    @auth_required(READ)
    def POST(self):
        """
        Searches based on a Criteria object. Requires a posted parameter
        'criteria' which has a data structure that can be turned into a
        Criteria instance.

        @param criteria:    Required. data structure that can be turned into
                            an instance of the Criteria model.
        @type  criteria:    dict

        @return:    list of matching users
        @rtype:     list
        """
        users = self._get_query_results_from_post(is_user_search=True)
        self._process_users(users)

        return self.ok(users)


urls = (
    '/search/$', 'UserSearch'
)
application = web.application(urls, globals())
