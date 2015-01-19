import unittest

from django.core.urlresolvers import resolve, Resolver404


class TestDjangoContentUrls(unittest.TestCase):

    def test_match_uploads_collection_view(self):
        """
        Test url matching for uploads collection.
        """
        match = resolve('/v2/content/uploads/')
        self.assertEqual(match.view_name, 'content_uploads')

        should_not_match = [
            '/v2/content/types/',
            '/v2/content/uploads',
            'v2/content/uploads/',
            '/content/uploads/',
            '/v2/content/uploads/extrastuff/',
            '/v2/content/uploads/extrastuff',
            '/v1/content/uploads/',
            '/v2/unit/uploads/',
        ]

        for url in should_not_match:
            # Urls should either raise a Resolver404 exception or match a url
            # that is not content_uploads
            try:
                match = resolve(url)
                self.assertNotEqual(match.view_name, 'content_uploads')
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

