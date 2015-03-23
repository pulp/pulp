import unittest

from django.core.urlresolvers import resolve, reverse, NoReverseMatch


def assert_url_match(expected_url, url_name, *args, **kwargs):
        """
        Generate a url given args and kwargs and pass it through Django's reverse and
        resolve functions.

        Example use to match a url /v2/tasks/<task_argument>/:
        assert_url_match('/v2/tasks/example_arg/', 'tasks', task_argument='example_arg')

        :param expected_url: the url that should be generated given a url_name and args
        :type  expected_url: str
        :param url_name    : name given to a url as defined in the urls.py
        :type  url_name    : str
        :param args        : optional positional arguments to place into a url's parameters
                             as specified by urls.py
        :type  args        : tuple
        :param kwargs      : optional named arguments to place into a url's parameters as
                             specified by urls.py
        :type  kwargs      : dict
        """
        try:
            # Invalid arguments will cause a NoReverseMatch.
            url = reverse(url_name, args=args, kwargs=kwargs)
        except NoReverseMatch:
            raise AssertionError(
                "Name: '{0}' could match a url with args '{1}'"
                "and kwargs '{2}'".format(url_name, args, kwargs)
            )

        else:
            # If the url exists but is not the expected url.
            if url != expected_url:
                raise AssertionError(
                    'url {0} not equal to expected url {1}'.format(url, expected_url))

            # Run this url back through resolve and ensure that it matches the url_name.
            matched_view = resolve(url)
            if matched_view.url_name != url_name:
                raise AssertionError('Url name {0} not equal to expected url name {1}'.format(
                    matched_view.url_name, url_name)
                )


class TestDjangoContentUrls(unittest.TestCase):
    """
    Test the matching of the content urls
    """

    def test_match_content_catalog_resource(self):
        """
        Test url matching for content_catalog_resource.
        """
        url = '/v2/content/catalog/mock-source/'
        url_name = 'content_catalog_resource'
        assert_url_match(url, url_name, source_id='mock-source')

    def test_match_content_orphan_collection(self):
        """
        Test url matching for content_orphan_collection.
        """
        url = '/v2/content/orphans/'
        url_name = 'content_orphan_collection'
        assert_url_match(url, url_name)

    def test_match_content_type_resource(self):
        """
        Test the url matching for content_type_resource.
        """
        url = '/v2/content/types/mock-type/'
        url_name = 'content_type_resource'
        assert_url_match(url, url_name, type_id='mock-type')

    def test_match_content_types(self):
        """
        Test the url matching for content_types.
        """
        url = '/v2/content/types/'
        url_name = 'content_types'
        assert_url_match(url, url_name)

    def test_match_content_units_collection(self):
        """
        Test the url matching for content_units_collection.
        """
        url = '/v2/content/units/mock-type/'
        url_name = 'content_units_collection'
        assert_url_match(url, url_name, type_id='mock-type')

    def test_match_content_unit_resource(self):
        """
        Test url matching for content_unit_resource.
        """
        url = '/v2/content/units/mock-type/mock-unit/'
        url_name = 'content_unit_resource'
        assert_url_match(url, url_name, type_id='mock-type', unit_id='mock-unit')

    def test_match_content_unit_user_metadata_resource(self):
        """
        Test url matching for content_unit_user_metadata_resourece.
        """
        url = '/v2/content/units/mock-type/mock-unit/pulp_user_metadata/'
        url_name = 'content_unit_user_metadata_resource'
        assert_url_match(url, url_name, type_id='mock-type', unit_id='mock-unit')

    def test_match_content_upload_resource(self):
        """
        Test url matching for content_upload_resource.
        """
        url = '/v2/content/uploads/mock-upload/'
        url_name = 'content_upload_resource'
        assert_url_match(url, url_name, upload_id='mock-upload')

    def test_match_content_upload_segment_resource(self):
        """
        Test Url matching for content_upload_segment_resource.
        """
        url = '/v2/content/uploads/mock-upload-id/8/'
        url_name = 'content_upload_segment_resource'
        assert_url_match(url, url_name, upload_id='mock-upload-id', offset='8')

    def test_match_content_actions_delete_orphans(self):
        """
        Test url matching for content_actions_delete_orphans.
        """
        url = '/v2/content/actions/delete_orphans/'
        url_name = 'content_actions_delete_orphans'
        assert_url_match(url, url_name)

    def test_match_content_orphan_resource(self):
        """
        Test url matching for content_orphan_resource.
        """
        url = '/v2/content/orphans/mock-type/mock-unit/'
        url_name = 'content_orphan_resource'
        assert_url_match(url, url_name, content_type='mock-type', unit_id='mock-unit')

    def test_match_content_orphan_type_subcollection(self):
        """
        Test url matching for content_orphan_type_subcollection.
        """
        url = '/v2/content/orphans/mock_type/'
        url_name = 'content_orphan_type_subcollection'
        assert_url_match(url, url_name, content_type='mock_type')

    def test_match_content_uploads(self):
        """
        Test url matching for content_uploads.
        """
        url = '/v2/content/uploads/'
        url_name = 'content_uploads'
        assert_url_match(url, url_name)


class TestDjangoPluginsUrls(unittest.TestCase):
    """
    Test url matching for plugins urls.
    """

    def test_match_distributor_resource_view(self):
        """
        Test the url matching for the distributor resource view.
        """
        url = '/v2/plugins/distributors/mock_distributor/'
        url_name = 'plugin_distributor_resource'
        assert_url_match(url, url_name, distributor_id='mock_distributor')

    def test_match_distributors_view(self):
        """
        Test the url matching for the Distributors view.
        """
        url = '/v2/plugins/distributors/'
        url_name = 'plugin_distributors'
        assert_url_match(url, url_name)

    def test_match_importer_resource_view(self):
        """
        Test the url matching for plugin_importer_resource
        """
        url = '/v2/plugins/importers/mock_importer_id/'
        url_name = 'plugin_importer_resource'
        assert_url_match(url, url_name, importer_id='mock_importer_id')

    def test_match_importers_view(self):
        """
        Test the url matching for the Importers view
        """
        url = '/v2/plugins/importers/'
        url_name = 'plugin_importers'
        assert_url_match(url, url_name)

    def test_match_type_resource_view(self):
        """
        Test the url matching for the TypeResourceView.
        """
        url = '/v2/plugins/types/type_id/'
        url_name = 'plugin_type_resource'
        assert_url_match(url, url_name, type_id='type_id')

    def test_match_types_view(self):
        """
        Test url matching for plugin_types.
        """
        url = '/v2/plugins/types/'
        url_name = 'plugin_types'
        assert_url_match(url, url_name)


class TestDjangoLoginUrls(unittest.TestCase):
    """
    Tests for root_actions urls.
    """

    def test_match_login_view(self):
        """
        Test url match for login.
        """
        url = '/v2/actions/login/'
        url_name = 'login'
        assert_url_match(url, url_name)


class TestDjangoConsumerGroupsUrls(unittest.TestCase):
    """
    Tests for consumer_groups urls
    """

    def test_match_consumer_group_view(self):
        """
        Test url matching for consumer_groups
        """
        url = '/v2/consumer_groups/'
        url_name = 'consumer_group'
        assert_url_match(url, url_name)

    def test_match_consumer_group_resource_view(self):
        """
        Test url matching for single consumer_group
        """
        url = '/v2/consumer_groups/test-group/'
        url_name = 'consumer_group_resource'
        assert_url_match(url, url_name, consumer_group_id='test-group')

    def test_match_consumer_group_associate_action_view(self):
        """
        Test url matching for consumer_groups association
        """
        url = '/v2/consumer_groups/test-group/actions/associate/'
        url_name = 'consumer_group_associate'
        assert_url_match(url, url_name, consumer_group_id='test-group')

    def test_match_consumer_group_unassociate_action_view(self):
        """
        Test url matching for consumer_groups unassociation
        """
        url = '/v2/consumer_groups/test-group/actions/unassociate/'
        url_name = 'consumer_group_unassociate'
        assert_url_match(url, url_name, consumer_group_id='test-group')

    def test_match_consumer_group_content_action_install_view(self):
        """
        Test url matching for consumer_groups content installation
        """
        url = '/v2/consumer_groups/test-group/actions/content/install/'
        url_name = 'consumer_group_content'
        assert_url_match(url, url_name, consumer_group_id='test-group', action='install')

    def test_match_consumer_group_content_action_update_view(self):
        """
        Test url matching for consumer_groups content update
        """
        url = '/v2/consumer_groups/test-group/actions/content/update/'
        url_name = 'consumer_group_content'
        assert_url_match(url, url_name, consumer_group_id='test-group', action='update')

    def test_match_consumer_group_content_action_uninstall_view(self):
        """
        Test url matching for consumer_groups content uninstall
        """
        url = '/v2/consumer_groups/test-group/actions/content/uninstall/'
        url_name = 'consumer_group_content'
        assert_url_match(url, url_name, consumer_group_id='test-group', action='uninstall')

    def test_match_consumer_group_bindings_view(self):
        """
        Test url matching for consumer_groups bindings
        """
        url = '/v2/consumer_groups/test-group/bindings/'
        url_name = 'consumer_group_bind'
        assert_url_match(url, url_name, consumer_group_id='test-group')

    def test_match_consumer_group_binding_view(self):
        """
        Test url matching for consumer_groups binding removal
        """
        url = '/v2/consumer_groups/test-group/bindings/repo1/dist1/'
        url_name = 'consumer_group_unbind'
        assert_url_match(url, url_name, consumer_group_id='test-group',
                         repo_id='repo1', distributor_id='dist1')


class TestDjangoRepoGroupsUrls(unittest.TestCase):
    """
    Test url matching for repo_groups urls
    """
    def test_match_repo_groups(self):
        """Test url matching for repo_groups."""
        url = '/v2/repo_groups/'
        url_name = 'repo_groups'
        assert_url_match(url, url_name)

    def test_match_repo_group_resource(self):
        url = '/v2/repo_groups/test-group-id/'
        url_name = 'repo_group_resource'
        assert_url_match(url, url_name, repo_group_id='test-group-id')

    def test_match_repo_group_associate(self):
        url = '/v2/repo_groups/test-group-id/actions/associate/'
        url_name = 'repo_group_associate'
        assert_url_match(url, url_name, repo_group_id='test-group-id')

    def test_match_repo_group_unassociate(self):
        url = '/v2/repo_groups/test-group-id/actions/unassociate/'
        url_name = 'repo_group_unassociate'
        assert_url_match(url, url_name, repo_group_id='test-group-id')

    def test_match_repo_group_distributors(self):
        url = '/v2/repo_groups/test-group-id/distributors/'
        url_name = 'repo_group_distributors'
        assert_url_match(url, url_name, repo_group_id='test-group-id')

    def test_match_repo_group_distributor_resource(self):
        url = '/v2/repo_groups/test-group-id/distributors/test-distributor/'
        url_name = 'repo_group_distributor_resource'
        assert_url_match(url, url_name, repo_group_id='test-group-id',
                         distributor_id='test-distributor')

    def test_repo_group_publish(self):
        url = '/v2/repo_groups/test-group-id/actions/publish/'
        url_name = 'repo_group_publish'
        assert_url_match(url, url_name, repo_group_id='test-group-id')


class TestDjangoTasksUrls(unittest.TestCase):
    """
    Test the matching for tasks urls.
    """

    def test_match_task_collection(self):
        """
        Test the matching for task_collection.
        """
        url = '/v2/tasks/'
        url_name = 'task_collection'
        assert_url_match(url, url_name)

    def test_match_task_resource(self):
        """
        Test the matching for task_resource.
        """
        url = '/v2/tasks/test-task/'
        url_name = 'task_resource'
        assert_url_match(url, url_name, task_id='test-task')


class TestDjangoRolesUrls(unittest.TestCase):
    """
    Tests for roles urls.
    """

    def test_match_roles_view(self):
        """
        Test url match for roles.
        """
        url = '/v2/roles/'
        url_name = 'roles'
        assert_url_match(url, url_name)

    def test_match_role_resource_view(self):
        """
        Test url matching for single role.
        """
        url = '/v2/roles/test-role/'
        url_name = 'role_resource'
        assert_url_match(url, url_name, role_id='test-role')

    def test_match_role_users_view(self):
        """
        Test url matching for role's users.
        """
        url = '/v2/roles/test-role/users/'
        url_name = 'role_users'
        assert_url_match(url, url_name, role_id='test-role')

    def test_match_role_user_view(self):
        """
        Test url matching for role's user.
        """
        url = '/v2/roles/test-role/users/test-login/'
        url_name = 'role_user'
        assert_url_match(url, url_name, role_id='test-role', login='test-login')


class TestDjangoPermissionsUrls(unittest.TestCase):
    """
    Tests for permissions urls
    """

    def test_match_permissions_view(self):
        """
        Test url matching for permissions
        """
        url = '/v2/permissions/'
        url_name = 'permissions'
        assert_url_match(url, url_name)

    def test_match_permission_grant_to_role_view(self):
        """
        Test url matching for grant permissions to a role
        """
        url = '/v2/permissions/actions/grant_to_role/'
        url_name = 'grant_to_role'
        assert_url_match(url, url_name)

    def test_match_permission_grant_to_user_view(self):
        """
        Test url matching for grant permissions to a user
        """
        url = '/v2/permissions/actions/grant_to_user/'
        url_name = 'grant_to_user'
        assert_url_match(url, url_name)

    def test_match_permission_revoke_from_role_view(self):
        """
        Test url matching for revoke permissions from a role
        """
        url = '/v2/permissions/actions/revoke_from_role/'
        url_name = 'revoke_from_role'
        assert_url_match(url, url_name)

    def test_match_permission_revoke_from_userview(self):
        """
        Test url matching for revoke permissions from a user
        """
        url = '/v2/permissions/actions/revoke_from_user/'
        url_name = 'revoke_from_user'
        assert_url_match(url, url_name)


class TestDjangoEventListenersUrls(unittest.TestCase):
    """
    Tests for events urls
    """

    def test_match_event_listeners_view(self):
        """
        Test url matching for event_listeners
        """
        url = '/v2/events/'
        url_name = 'events'
        assert_url_match(url, url_name)

    def test_match_event_listeners_resource_view(self):
        """
        Test url matching for single event_listener
        """
        url = '/v2/events/12345/'
        url_name = 'event_resource'
        assert_url_match(url, url_name, event_listener_id='12345')


class TestDjangoUsersUrls(unittest.TestCase):
    """
    Tests for userss urls
    """

    def test_match_users_view(self):
        """
        Test url matching for users
        """
        url = '/v2/users/'
        url_name = 'users'
        assert_url_match(url, url_name)

    def test_match_user_resource(self):
        """
        Test the matching for user resource.
        """
        url = '/v2/users/user_login/'
        url_name = 'user_resource'
        assert_url_match(url, url_name, login='user_login')


class TestStatusUrl(unittest.TestCase):
    """
    Tests for server status url
    """

    def test_match_users_view(self):
        """
        Test url matching for status
        """
        url = '/v2/status/'
        url_name = 'status'
        assert_url_match(url, url_name)
