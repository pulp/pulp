import unittest

from django.core.urlresolvers import resolve, Resolver404


class TestDjangoUrls(unittest.TestCase):

    def test_match_delete_orphans_view(self):

        match = resolve('/v2/content/actions/delete_orphans/')
        self.assertEqual(match.url_name, 'delete_orphans')

        should_not_match = [
            '/v2/content/actions/',
            '/content/actions/delete_orphans/',
            'v2/content/actions/delete_orphans/',
            '/v2/content/delete_orphans/',
        ]

        for url in should_not_match:
            # Urls should either raise a Resolver404 exception or match a url
            # that is not delete_orphans
            try:
                match = resolve(url)
                self.assertNotEqual(match.url_name, 'delete_orphans')
            except Resolver404:
                self.assertTrue(True)
