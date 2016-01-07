import unittest

from django.core.urlresolvers import resolve, reverse, NoReverseMatch

from pulp.server.webservices.urls import handler404


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


class TestNotFoundHandler(unittest.TestCase):

    def test_not_found_handler(self):
        """
        Test that the handler404 module attribute is set as expected.
        """
        self.assertEqual(handler404, 'pulp.server.webservices.views.util.page_not_found')


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

    def test_match_content_units_collection(self):
        """
        Test the url matching for content_units_collection.
        """
        url = '/v2/content/units/mock-type/'
        url_name = 'content_units_collection'
        assert_url_match(url, url_name, type_id='mock-type')

    def test_match_content_unit_search(self):
        """
        Test the url matching for content_unit_search.
        """
        url = '/v2/content/units/mock-type/search/'
        url_name = 'content_unit_search'
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
        Test url matching for content_unit_user_metadata_resource.
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

    def test_match_consumer_group_search_view(self):
        """
        Test url matching for consumer_group_search
        """
        url = '/v2/consumer_groups/search/'
        url_name = 'consumer_group_search'
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


class TestDjangoRepositoriesUrls(unittest.TestCase):
    """
    Test url matching for repositories urls.
    """

    def test_match_repos(self):
        """
        Test url matching for repos.
        """
        url = '/v2/repositories/'
        url_name = 'repos'
        assert_url_match(url, url_name)

    def test_match_repo_search(self):
        """
        Test url matching for repo_search.
        """
        url = '/v2/repositories/search/'
        url_name = 'repo_search'
        assert_url_match(url, url_name)

    def test_match_repo_content_app_regen(self):
        """
        Test url matching for repo_content_app_regen.
        """
        url_name = 'repo_content_app_regen'
        url = '/v2/repositories/actions/content/regenerate_applicability/'
        assert_url_match(url, url_name)

    def test_match_repo_resource(self):
        """
        Test url matching for repo_resource.
        """
        url_name = 'repo_resource'
        url = '/v2/repositories/mock_repo/'
        assert_url_match(url, url_name, repo_id='mock_repo')

    def test_match_repo_unit_search(self):
        """
        Test url matching for repo_unit_search.
        """
        url_name = 'repo_unit_search'
        url = '/v2/repositories/mock_repo/search/units/'
        assert_url_match(url, url_name, repo_id='mock_repo')

    def test_match_repo_importers(self):
        """
        Test url matching for repo_importers.
        """
        url_name = 'repo_importers'
        url = '/v2/repositories/mock_repo/importers/'
        assert_url_match(url, url_name, repo_id='mock_repo')

    def test_match_repo_importer_resource(self):
        """
        Test url matching for repo_importer_resource.
        """
        url = '/v2/repositories/mock_repo/importers/mock_importer/'
        url_name = 'repo_importer_resource'
        assert_url_match(url, url_name, repo_id='mock_repo', importer_id='mock_importer')

    def test_match_repo_sync_schedule_collection(self):
        """
        Test url matching for repo_sync_schedules.
        """
        url = '/v2/repositories/mock_repo/importers/mock_importer/schedules/sync/'
        url_name = 'repo_sync_schedules'
        assert_url_match(url, url_name, repo_id='mock_repo', importer_id='mock_importer')

    def test_match_repo_sync_schedule_resource(self):
        """
        Test url matching for repo_sync_schedule_resource.
        """
        url = '/v2/repositories/mock_repo/importers/mock_importer/schedules/sync/mock_schedule/'
        url_name = 'repo_sync_schedule_resource'
        assert_url_match(url, url_name, repo_id='mock_repo', importer_id='mock_importer',
                         schedule_id='mock_schedule')

    def test_match_repo_distributors(self):
        """
        Test url matching for repo_distributors.
        """
        url = '/v2/repositories/mock_repo/distributors/'
        url_name = 'repo_distributors'
        assert_url_match(url, url_name, repo_id='mock_repo')

    def test_match_repo_distributor_resource(self):
        """
        Test url matching for repo_distributor_resource.
        """
        url = '/v2/repositories/mock_repo/distributors/mock_distributor/'
        url_name = 'repo_distributor_resource'
        assert_url_match(url, url_name, repo_id='mock_repo', distributor_id='mock_distributor')

    def test_match_repo_publish_schedules(self):
        """
        Test url matching for repo_publish_schedules.
        """
        url = '/v2/repositories/mock_repo/distributors/mock_distributor/schedules/publish/'
        url_name = 'repo_publish_schedules'
        assert_url_match(url, url_name, repo_id='mock_repo', distributor_id='mock_distributor')

    def test_match_repo_publish_schedule_resource(self):
        """
        Test url matching for repo_publish_schedule_resource.
        """
        url = '/v2/repositories/mock_repo/distributors/'\
              'mock_distributor/schedules/publish/mock_schedule/'
        url_name = 'repo_publish_schedule_resource'
        assert_url_match(url, url_name, repo_id='mock_repo', distributor_id='mock_distributor',
                         schedule_id='mock_schedule')

    def test_match_repo_sync_history(self):
        """
        Test url matching for repo_sync_history.
        """
        url = '/v2/repositories/mock_repo/history/sync/'
        url_name = 'repo_sync_history'
        assert_url_match(url, url_name, repo_id='mock_repo')

    def test_match_repo_sync(self):
        """
        Test url matching for repo_sync.
        """
        url = '/v2/repositories/mock_repo/actions/sync/'
        url_name = 'repo_sync'
        assert_url_match(url, url_name, repo_id='mock_repo')

    def test_match_repo_download(self):
        """
        Test url matching for repo_download.
        """
        url = '/v2/repositories/mock_repo/actions/download/'
        url_name = 'repo_download'
        assert_url_match(url, url_name, repo_id='mock_repo')

    def test_match_repo_publish_history(self):
        """
        Test url matching for repo_publish_history.
        """
        url = '/v2/repositories/mock_repo/history/publish/mock_dist/'
        url_name = 'repo_publish_history'
        assert_url_match(url, url_name, repo_id='mock_repo', distributor_id='mock_dist')

    def test_match_repo_publish(self):
        """
        Test url matching for repo_publish.
        """
        url = '/v2/repositories/mock_repo/actions/publish/'
        url_name = 'repo_publish'
        assert_url_match(url, url_name, repo_id='mock_repo')

    def test_match_repo_associate(self):
        """
        Test url matching for repo_associate.
        """
        url = '/v2/repositories/mock_repo/actions/associate/'
        url_name = 'repo_associate'
        assert_url_match(url, url_name, dest_repo_id='mock_repo')

    def test_match_repo_unassociate(self):
        """
        Test url matching for repo_unassociate.
        """
        url = '/v2/repositories/mock_repo/actions/unassociate/'
        url_name = 'repo_unassociate'
        assert_url_match(url, url_name, repo_id='mock_repo')

    def test_match_repo_import_upload(self):
        """
        Test url matching for repo_import_upload.
        """
        url = '/v2/repositories/mock_repo/actions/import_upload/'
        url_name = 'repo_import_upload'
        assert_url_match(url, url_name, repo_id='mock_repo')


class TestDjangoRepoGroupsUrls(unittest.TestCase):
    """
    Test url matching for repo_groups urls
    """
    def test_match_repo_groups(self):
        """Test url matching for repo_groups."""
        url = '/v2/repo_groups/'
        url_name = 'repo_groups'
        assert_url_match(url, url_name)

    def test_match_repo_group_search(self):
        """Test url matching for repo_group_search."""
        url = '/v2/repo_groups/search/'
        url_name = 'repo_group_search'
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

    def test_match_task_search(self):
        """
        Test the matching for task_resource.
        """
        url = '/v2/tasks/search/'
        url_name = 'task_search'
        assert_url_match(url, url_name)


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

    def test_match_user_search_view(self):
        """
        Test url matching for user search.
        """
        url = '/v2/users/search/'
        url_name = 'user_search'
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

    def test_match_status_view(self):
        """
        Test url matching for status
        """
        url = '/v2/status/'
        url_name = 'status'
        assert_url_match(url, url_name)


class TestDjangoConsumersUrls(unittest.TestCase):
    """
    Tests for consumers urls
    """

    def test_match_consumers_view(self):
        """
        Test url matching for consumer
        """
        url = '/v2/consumers/'
        url_name = 'consumers'
        assert_url_match(url, url_name)

    def test_match_consumer_search(self):
        """
        Test url matching for consumer_search.
        """
        url = '/v2/consumers/search/'
        url_name = 'consumer_search'
        assert_url_match(url, url_name)

    def test_match_consumer_resource_view(self):
        """
        Test url matching for consumer resource.
        """
        url = '/v2/consumers/test-consumer/'
        url_name = 'consumer_resource'
        assert_url_match(url, url_name, consumer_id='test-consumer')

    def test_match_consumer_search_view(self):
        """
        Test url matching for consumer search.
        """
        url = '/v2/consumers/search/'
        url_name = 'consumer_search'
        assert_url_match(url, url_name)

    def test_match_consumer_binding_search_view(self):
        """
        Test url matching for consumer binding search.
        """
        url = '/v2/consumers/binding/search/'
        url_name = 'consumer_binding_search'
        assert_url_match(url, url_name)

    def test_match_consumer_profile_search_view(self):
        """
        Test url matching for consumer profile search.
        """
        url = '/v2/consumers/profile/search/'
        url_name = 'consumer_profile_search'
        assert_url_match(url, url_name)

    def test_match_consumer_profiles_view(self):
        """
        Test url matching for consumer profiles
        """
        url = '/v2/consumers/test-consumer/profiles/'
        url_name = 'consumer_profiles'
        assert_url_match(url, url_name, consumer_id='test-consumer')

    def test_match_consumer_profile_resource_view(self):
        """
        Test url matching for consumer profile resource
        """
        url = '/v2/consumers/test-consumer/profiles/some-profile/'
        url_name = 'consumer_profile_resource'
        assert_url_match(url, url_name, consumer_id='test-consumer', content_type='some-profile')

    def test_match_consumer_bindings_view(self):
        """
        Test url matching for consumer bindings
        """
        url = '/v2/consumers/test-consumer/bindings/'
        url_name = 'bindings'
        assert_url_match(url, url_name, consumer_id='test-consumer')

    def test_match_consumer_binding_resource_view(self):
        """
        Test url matching for consumer binding resource
        """
        url = '/v2/consumers/test-consumer/bindings/some-repo/some-dist/'
        url_name = 'consumer_binding_resource'
        assert_url_match(url, url_name, consumer_id='test-consumer', repo_id='some-repo',
                         distributor_id='some-dist')

    def test_match_consumer_binding_repo_view(self):
        """
        Test url matching for consumer and repo binding
        """
        url = '/v2/consumers/test-consumer/bindings/some-repo/'
        url_name = 'bindings_repo'
        assert_url_match(url, url_name, consumer_id='test-consumer', repo_id='some-repo')

    def test_match_consumer_appicability_regen_view(self):
        """
        Test url matching for consumer applicability renegeration
        """
        url = '/v2/consumers/test-consumer/actions/content/regenerate_applicability/'
        url_name = 'consumer_appl_regen'
        assert_url_match(url, url_name, consumer_id='test-consumer')

    def test_match_consumer_content_action_install_view(self):
        """
        Test url matching for consumer content installation
        """
        url = '/v2/consumers/test-consumer/actions/content/install/'
        url_name = 'consumer_content'
        assert_url_match(url, url_name, consumer_id='test-consumer', action='install')

    def test_match_consumer_content_action_update_view(self):
        """
        Test url matching for consumer content update
        """
        url = '/v2/consumers/test-consumer/actions/content/update/'
        url_name = 'consumer_content'
        assert_url_match(url, url_name, consumer_id='test-consumer', action='update')

    def test_match_consumer_content_action_uninstall_view(self):
        """
        Test url matching for consumer content uninstall
        """
        url = '/v2/consumers/test-consumer/actions/content/uninstall/'
        url_name = 'consumer_content'
        assert_url_match(url, url_name, consumer_id='test-consumer', action='uninstall')

    def test_match_consumers_appicability_regen_view(self):
        """
        Test url matching for consumers applicability renegeration
        """
        url = '/v2/consumers/actions/content/regenerate_applicability/'
        url_name = 'appl_regen'
        assert_url_match(url, url_name)

    def test_match_consumer_query_appicability_view(self):
        """
        Test url matching for consumer query applicability
        """
        url = '/v2/consumers/content/applicability/'
        url_name = 'consumer_query_appl'
        assert_url_match(url, url_name)

    def test_match_consumer_schedule_content_action_install_view(self):
        """
        Test url matching for consumer schedule content installation
        """
        url = '/v2/consumers/test-consumer/schedules/content/install/'
        url_name = 'schedule_content_install'
        assert_url_match(url, url_name, consumer_id='test-consumer')

    def test_match_consumer_schedule_content_action_update_view(self):
        """
        Test url matching for consumer schedule  content update
        """
        url = '/v2/consumers/test-consumer/schedules/content/update/'
        url_name = 'schedule_content_update'
        assert_url_match(url, url_name, consumer_id='test-consumer')

    def test_match_consumer_schedule_content_action_uninstall_view(self):
        """
        Test url matching for consumer schedule content uninstall
        """
        url = '/v2/consumers/test-consumer/schedules/content/uninstall/'
        url_name = 'schedule_content_uninstall'
        assert_url_match(url, url_name, consumer_id='test-consumer')

    def test_match_consumer_schedule_content_action_install_resource_view(self):
        """
        Test url matching for consumer schedule content resource installation
        """
        url = '/v2/consumers/test-consumer/schedules/content/install/12345/'
        url_name = 'schedule_content_install_resource'
        assert_url_match(url, url_name, consumer_id='test-consumer', schedule_id='12345')

    def test_match_consumer_schedule_content_action_update_resource_view(self):
        """
        Test url matching for consumer schedule content resource update
        """
        url = '/v2/consumers/test-consumer/schedules/content/update/12345/'
        url_name = 'schedule_content_update_resource'
        assert_url_match(url, url_name, consumer_id='test-consumer', schedule_id='12345')

    def test_match_consumer_schedule_content_action_uninstall_resource_view(self):
        """
        Test url matching for consumer schedule content resource uninstall
        """
        url = '/v2/consumers/test-consumer/schedules/content/uninstall/12345/'
        url_name = 'schedule_content_uninstall_resource'
        assert_url_match(url, url_name, consumer_id='test-consumer', schedule_id='12345')

    def test_match_consumer_history_view(self):
        """
        Test url matching for consumer history
        """
        url = '/v2/consumers/test-consumer/history/'
        url_name = 'consumer_history'
        assert_url_match(url, url_name, consumer_id='test-consumer')


class TestDjangoContentSourcesUrls(unittest.TestCase):
    """
    Tests for content sources.
    """

    def test_match_content_sources_view(self):
        """
        Test url matching for content sources.
        """
        url = '/v2/content/sources/'
        url_name = 'content_sources'
        assert_url_match(url, url_name)

    def test_match_content_sources_resource(self):
        """
        Test the matching for content sources resource.
        """
        url = '/v2/content/sources/some-source/'
        url_name = 'content_sources_resource'
        assert_url_match(url, url_name, source_id='some-source')

    def test_match_content_sources_refresh_view(self):
        """
        Test url matching for content sources refresh.
        """
        url = '/v2/content/sources/action/refresh/'
        url_name = 'content_sources_action'
        assert_url_match(url, url_name, action='refresh')

    def test_match_content_sources_resource_refresh(self):
        """
        Test the matching for content sources resource refresh.
        """
        url = '/v2/content/sources/some-source/action/refresh/'
        url_name = 'content_sources_resource_action'
        assert_url_match(url, url_name, source_id='some-source', action='refresh')
