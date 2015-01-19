import unittest

from django.core.urlresolvers import resolve, Resolver404


class TestDjangoContentUrls(unittest.TestCase):

    def test_match_content_unit_resource_view(self):
        """
        Test url matching for content unit resource view.
        """
        base_url = '/v2/content/units/'
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
            '/v2/content/units/',
            '/v2/content/units//',
            '/content/units/var/var/',
            '/v2/content/units/ok/ok/notok/',
            '/v1/content/units///',
            '/v2/content/units/rpm/',
        ]

        for type_id, unit_id in should_match:
            match = resolve(base_url + type_id + '/' + unit_id + '/')
            self.assertEqual(match.view_name, 'content_unit_resource')
            self.assertEqual(match.kwargs['type_id'], type_id)
            self.assertEqual(match.kwargs['unit_id'], unit_id)

        for url in should_not_match:
            # Urls should either raise a Resolver404 exception or match a url
            # that is not content_unit_resource
            try:
                match = resolve(url)
                self.assertNotEqual(match.view_name, 'content_unit_resource')
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
