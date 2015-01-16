import unittest

from django.core.urlresolvers import resolve, Resolver404


class TestDjangoContentUrls(unittest.TestCase):

    def test_match_orphan_resource(self):
        base_url = '/v2/content/orphans/'
        should_match = [
            ('words', 'other_words'),
            ('a', 'b'),
            ('!@#$%^&***()_=', '$#%'),
            ('periods.too', '.'),
            ('spaces are ok', 'yes they are'),
            ('340593845', '34534'),
            (' ', ' '),
            ('UPPPERCASE', 'uppercase'),
        ]
        should_not_match = [
            '/v2/content/orphans/',
            '/v2/content/orphans//',
            '/content/orphans/var/var/',
            '/v2/content/orphans/ok/ok/notok/',
            '/v1/content/orphans///',
            '/v2/content/units/thing/thing/',
        ]

        for content_type, unit_id in should_match:
            match = resolve(base_url + content_type + '/' + unit_id + '/')
            self.assertEqual(match.view_name, 'orphan_resource')
            self.assertEqual(match.kwargs['content_type'], content_type)
            self.assertEqual(match.kwargs['unit_id'], unit_id)

        for url in should_not_match:
            # Urls should either raise a Resolver404 exception or match a url
            # that is not orphan_resource 
            try:
                match = resolve(url)
                self.assertNotEqual(match.view_name, 'orphan_resource')
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

