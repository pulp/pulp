import unittest

from django.core.urlresolvers import resolve, Resolver404


class TestDjangoContentUrls(unittest.TestCase):

    def test_match_orphan_type_subcollection_view(self):
        base_url = '/v2/content/orphans/'
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
            '/v2/content/orphans/',
            '/v2/content/orphans//',
            '/content/orphans/var/',
            '/v2/content/orphans/ok/notok/',
            '/v1/content/orphans///',
            '/v2/content/units/rpm/',
        ]

        for content_type_id in should_match:
            match = resolve(base_url + content_type_id + '/')
            self.assertEqual(match.view_name, 'orphan_type_subcollection')
            self.assertEqual(match.kwargs['content_type_id'], content_type_id)

        for url in should_not_match:
            # Urls should either raise a Resolver404 exception or match a url
            # that is not orphan_type_subcollection 
            try:
                match = resolve(url)
                self.assertNotEqual(match.view_name, 'orphan_type_subcollection')
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

