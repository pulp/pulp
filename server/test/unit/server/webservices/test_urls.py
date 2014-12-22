import unittest

from django.core.urlresolvers import resolve, Resolver404


class TestDjangoUrls(unittest.TestCase):

    def test_match_content_upload_resource_view(self):
        base_url = '/v2/content/uploads/'
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
            '/v2/content/uploads/',
            '/v2/content/uploads//',
            '/content/uploads/var/',
            '/v2/content/uploads/ok/notok/',
            '/v1/content/uploads///',
            '/v2/content/types/rpm/',
        ]

        for upload_id in should_match:
            match = resolve(base_url + upload_id + '/')
            self.assertEqual(match.view_name, 'content_upload_resource')
            self.assertEqual(match.kwargs['upload_id'], upload_id)

        for url in should_not_match:
            # Urls should either raise a Resolver404 exception or match a url
            # that is not content_types
            try:
                match = resolve(url)
                self.assertNotEqual(match.view_name, 'content_upload_resource')
            except Resolver404:
                self.assertTrue(True)
