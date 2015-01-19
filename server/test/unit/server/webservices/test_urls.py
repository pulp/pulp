import unittest

from django.core.urlresolvers import resolve, Resolver404


class TestDjangoContentUrls(unittest.TestCase):

    def test_match_delete_orphans_view(self):
        """
        Test url matching for /content/actions/delete_orphans/
        """
        match = resolve('/v2/content/actions/delete_orphans/')
        self.assertEqual(match.url_name, 'content_actions_delete_orphans')

        should_not_match = [
            '/v2/content/actions/',
            '/content/actions/delete_orphans/',
            'v2/content/actions/delete_orphans/',
            '/v2/content/delete_orphans/',
        ]

        for url in should_not_match:
            # Urls should either raise a Resolver404 exception or match a url
            # that is not content_actions_delete_orphans
            try:
                match = resolve(url)
                self.assertNotEqual(match.url_name, 'content_actions_delete_orphans')
            except Resolver404:
                self.assertTrue(True)


class TestDjangoPluginsUrls(unittest.TestCase):

    def test_match_distributor_resource_view(self):
        pass

    def test_match_distributors_view(self):
        pass

    def test_match_importer_resource_view(self):
        pass

    def test_match_importers_view(self):
        pass

    def test_match_type_resource_view(self):
        pass

    def test_match_types_view(self):
        pass

