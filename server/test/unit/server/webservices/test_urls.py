import unittest

from django.core.urlresolvers import resolve, Resolver404


class TestDjangoContentUrls(unittest.TestCase):

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

    def test_match_content_type_resource_view(self):
        base_url = '/v2/content/types/'
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
            '/v2/content/types/',
            '/v2/content/types//',
            '/content/types/var/',
            '/v2/content/types/ok/notok/',
            '/v1/content/types///',
            '/v2/content/units/rpm/',
        ]

        for type_id in should_match:
            match = resolve(base_url + type_id + '/')
            self.assertEqual(match.view_name, 'content_type_resource')
            self.assertEqual(match.kwargs['type_id'], type_id)

        for url in should_not_match:
            # Urls should either raise a Resolver404 exception or match a url
            # that is not content_types
            try:
                match = resolve(url)
                self.assertNotEqual(match.view_name, 'content_type+resource')
            except Resolver404:
                self.assertTrue(True)

    def test_match_content_units_collectiom_view(self):
        base_url = '/v2/content/units/'
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
            '/v2/content/types/',
            '/v2/content/units//',
            '/content/units/var/',
            '/v2/content/units/ok/notok/',
            '/v1/content/units///',
            '/v2/content/types/rpm/',
        ]

        for type_id in should_match:
            match = resolve(base_url + type_id + '/')
            self.assertEqual(match.view_name, 'content_units_collection')
            self.assertEqual(match.kwargs['type_id'], type_id)

        for url in should_not_match:
            # Urls should either raise a Resolver404 exception or match a url
            # that is not content_types
            try:
                match = resolve(url)
                self.assertNotEqual(match.view_name, 'content_units_collection')
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

