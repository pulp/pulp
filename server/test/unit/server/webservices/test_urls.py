import unittest

from django.core.urlresolvers import resolve, Resolver404


class TestDjangoUrls(unittest.TestCase):

    def test_match_catalog_resource(self):

        base_url = '/v2/content/catalog/'
        should_match = [
            'words',
            'a',
            '!@#$%^&***()_=',
            'periods.too',
            'spaces are ok',
            '340593845',
            ' ',
            'UPPPERCASE',
        ]
        should_not_match = [
            '/v2/content/catalog/',
            '/v2/content/catalog//',
            '/content/catalog/var/',
            '/v2/content/catalog/ok/notok/',
            '/v1/content/catalog///',
            '/v2/content/types/rpm/',
        ]

        for source_id in should_match:
            match = resolve(base_url + source_id + '/')
            self.assertEqual(match.url_name, 'catalog_resource')
            self.assertEqual(match.kwargs['source_id'], source_id)

        for url in should_not_match:
            # Urls should either raise a Resolver404 or match a url that is not catalog resource.
            try:
                match = resolve(url)
                self.assertNotEqual(match.view_name, 'catalog_resource')
            except Resolver404:
                self.assertTrue(True):

