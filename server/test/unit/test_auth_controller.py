import mock

import base

from pulp.server.db.connection import PulpCollection
from pulp.server.db.model import criteria
from pulp.server.db.model.auth import (User, Role, Permission)
from pulp.server.managers import factory as manager_factory
from pulp.server.webservices.controllers import users


class AuthControllersTests(base.PulpWebserviceTests):

    def setUp(self):
        super(AuthControllersTests, self).setUp()
        self.user_manager = manager_factory.user_manager()
        self.user_query_manager = manager_factory.user_query_manager()
        self.role_manager = manager_factory.role_manager()
        self.role_query_manager = manager_factory.role_query_manager()
        self.permission_manager = manager_factory.permission_manager()
        self.permission_query_manager = manager_factory.permission_query_manager()
        self.password_manager = manager_factory.password_manager()

        self.role_manager.ensure_super_user_role()
        self.user_manager.ensure_admin()

    def clean(self):
        super(AuthControllersTests, self).clean()
        User.get_collection().remove(safe=True)
        Role.get_collection().remove(safe=True)
        Permission.get_collection().remove(safe=True)


class UserSearchTests(AuthControllersTests):
    USER_LOGINS = 'user1', 'user2'
    ROLE_ID = 'role1'
    FILTER = {'login':{'$in':USER_LOGINS}}
    SORT = [('login','ascending')]
    CRITERIA = dict(filters=FILTER, sort=SORT)
    
    def populate(self):
        role_manager = manager_factory.role_manager()
        role_manager.create_role(self.ROLE_ID)
        
        for login in self.USER_LOGINS:
            user_manager = manager_factory.user_manager()
            user_manager.create_user(login=login, password=login, roles=[self.ROLE_ID])
    
    def validate(self, body, user_count=None):
        if user_count is None:
            user_count = len(self.USER_LOGINS)
        self.assertEqual(user_count, len(body))
        fetched = dict([(u['login'], u) for u in body])
        for login in self.USER_LOGINS:
            user = fetched[login]
            self.assertEquals(user['login'], login)
            self.assertTrue('_href' in user)
            self.assertTrue('roles' in user)
            roles = user['roles']
            self.assertEquals(len(roles), 1)
            self.assertEquals(roles[0], self.ROLE_ID)

    @mock.patch.object(users.UserSearch, 'params')
    @mock.patch.object(PulpCollection, 'query')
    def test_basic_search(self, mock_query, mock_params):
        mock_params.return_value = {
            'criteria' : {}
        }
        ret = self.post('/v2/users/search/')
        self.assertEqual(ret[0], 200)
        self.assertEqual(mock_query.call_count, 1)
        query_arg = mock_query.call_args[0][0]
        self.assertTrue(isinstance(query_arg, criteria.Criteria))
        # one call each for criteria, importers, and distributors
        self.assertEqual(mock_params.call_count, 1)


    @mock.patch.object(PulpCollection, 'query')
    @mock.patch('pulp.server.db.model.criteria.Criteria.from_client_input')
    def test_get_limit(self, mock_from_client, mock_query):
        status, body = self.get('/v2/users/search/?limit=2')
        self.assertEqual(status, 200)
        self.assertEquals(mock_from_client.call_count, 1)

        # make sure the non-criteria arguments aren't passed to the criteria
        # constructor
        criteria_args = mock_from_client.call_args[0][0]
        self.assertTrue('limit' in criteria_args)


    @mock.patch.object(users.UserSearch, 'params')
    @mock.patch.object(PulpCollection, 'query')
    def test_return_value(self, mock_query, mock_params):
        """
        make sure the method returns the same stuff that is returned by query()
        """
        mock_params.return_value = {
            'criteria' : {}
        }
        mock_query.return_value = [
            {'login' : 'user-1'},
            {'login' : 'user-2'},
        ]
        ret = self.post('/v2/users/search/')
        self.assertEqual(ret[0], 200)
        self.assertEqual(ret[1], mock_query.return_value)


    @mock.patch.object(users.UserSearch, 'params', return_value={})
    def test_require_criteria(self, mock_params):
        """
        make sure this raises a MissingValue exception if 'criteria' is not
        passed as a parameter.
        """
        ret = self.post('/v2/users/search/')
        self.assertEqual(ret[0], 400)
        value = ret[1]
        self.assertTrue(isinstance(value, dict))
        self.assertTrue('missing_property_names' in value)
        self.assertEqual(value['missing_property_names'], [u'criteria'])


    @mock.patch.object(PulpCollection, 'query')
    def test_get_users(self, mock_query):
        """
        Make sure that we can do a criteria-based search with GET. Ensures that
        a proper Criteria object is created and passed to the collection's
        query method.
        """
        status, body = self.get(
            '/v2/users/search/?field=login&field=name&limit=20')
        self.assertEqual(status, 200)
        self.assertEqual(mock_query.call_count, 1)
        generated_criteria = mock_query.call_args[0][0]
        self.assertTrue(isinstance(generated_criteria, criteria.Criteria))
        self.assertEqual(len(generated_criteria.fields), 2)
        self.assertTrue('login' in generated_criteria.fields)
        self.assertTrue('name' in generated_criteria.fields)
        self.assertEqual(generated_criteria.limit, 20)
        self.assertTrue(generated_criteria.skip is None)

    def test_get(self):
        # Setup
        self.populate()
        # Test
        status, body = self.get('/v2/users/search/')
        # Verify
        self.assertEqual(200, status)
        self.validate(body, 3)

    def test_post(self):
        # Setup
        self.populate()
        # Test
        body = {'criteria':self.CRITERIA}
        status, body = self.post('/v2/users/search/', body)
        # Verify
        self.validate(body)

    def test_post_with_details(self):
        # Setup
        self.populate()
        # Test
        body = {'criteria':self.CRITERIA, 'details':True}
        status, body = self.post('/v2/users/search/', body)
        # Verify
        self.assertEqual(200, status)
        self.validate(body)

    def test_post_with_roles(self):
        # Setup
        self.populate()
        # Test
        body = {'criteria':self.CRITERIA, 'roles':True}
        status, body = self.post('/v2/users/search/', body)
        # Verify
        self.assertEqual(200, status)
        self.validate(body)



