import unittest

from django.core.urlresolvers import resolve, Resolver404


class TestDjangoUrls(unittest.TestCase):

    def test_match_uploads_collection_view(self):
        match = resolve('/v2/content/uploads/')
        self.assertEqual(match.view_name, 'uploads_collection_view')

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
            # that is not content_types
            try:
                match = resolve(url)
                self.assertNotEqual(match.view_name, 'uploads_collection_view')
            except Resolver404:
                self.assertTrue(True)
