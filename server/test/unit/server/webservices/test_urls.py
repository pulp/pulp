import unittest

from django.core.urlresolvers import resolve, reverse, NoReverseMatch


def assert_url_match(expected_url, url_name, *args, **kwargs):
        """
        Generate a url given args and kwargs and pass it through Django's reverse and
        resolve functions.

        Example use to match a url /v2/tasks/<task_argument>/:
        assert_url_match('/v2/tasks/example_arg/', 'tasks', task_argument='example_arg')

        :param expected_url: the url that should be generated given a url_name and args
        :type  expected_url: string
        :param url_name    : name given to a url as defined in the urls.py
        :type  url_name    : string
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

        symbols_url = '/v2/plugins/importers/%21/'
        url_name = 'plugin_importer_resource'
        assert_url_match(symbols_url, url_name, importer_id='!')

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

        url_with_symbol = '/v2/plugins/types/%21/'
        assert_url_match(url_with_symbol, url_name, type_id='!')

    def test_match_types_view(self):
        """
        Test url matching for plugin_types.
        """
        url = '/v2/plugins/types/'
        url_name = 'plugin_types'
        assert_url_match(url, url_name)


class TestDjangoRepoGroupsUrls(unittest.TestCase):
    """
    Test url matching for /repo_groups/*
    """

    def test_match_repo_groups(self):
        pass

    def test_match_repo_group_resource(self):
        pass

    def test_match_repo_group_associate(self):
        pass

    def test_match_repo_group_unassociate(self):
        pass

    def test_match_repo_group_distributors(self):
        pass

    def test_match_repo_group_distributor_resource(self):
        pass

    def test_repo_group_publish(self):
        pass


class TestDjangoRepositoriesUrls(unittest.TestCase):

    def test_match_repositories_resource_sync(self):
        url = '/v2/repositories/a1b2%21/actions/sync/'
        url_name = 'repositories_resource_sync'
        assert_url_match(url, url_name, repo_id='a1b2!')


class TestDjangoTasksUrls(unittest.TestCase):

    def test_match_tasks_url(self):
        url = '/v2/tasks/'
        url_name = 'tasks'
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
        url_name = 'login_view'
        assert_url_match(url, url_name)
