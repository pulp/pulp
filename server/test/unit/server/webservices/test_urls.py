# TODO(asmacdo) remove to
# Required to tell django where the settings module is.
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'pulp.server.webservices.settings'

import unittest

from django.core.urlresolvers import resolve, Resolver404


class TestDjangoUrls(unittest.TestCase):

    def test_match_content_types_view(self):
        match = resolve('/v2/content/types/')
        self.assertEqual(match.view_name, 'content_types')

        should_not_match = [
            'v2/content/types/',
            '/v2/content/types',
            '/content/types/',
            '/v2/content/types/extrastuff/',
            '/v2/content/types/extrastuff',
            '/v1/content/types/',
            '/v2/unit/types/',
            '/v2/content/types/rpm/',
        ]

        for url in should_not_match:
            # Urls should either raise a Resolver404 exception or match a url
            # that is not content_types
            try:
                match = resolve(url)
                self.assertNotEqual(match.view_name, 'content_types')
            except Resolver404:
                self.assertTrue(True)