
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'pulp.server.webservices.settings'

import unittest

from django.core.urlresolvers import resolve


class TestDjangoUrls(unittest.TestCase):

    def test_content_types_view(self):
        match = resolve('/v2/content/types/')
        self.assertEqual(match.view_name, 'content_types')