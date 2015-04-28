import unittest

import mock

from pulp.server.webservices.views.serializers import link


class TestSerializationLink(unittest.TestCase):
    @mock.patch('pulp.server.webservices.http.uri_path', return_value='/base/uri/repo1/')
    def test_current_link_obj(self, mock_path):
        ret = link.current_link_obj()
        self.assertEqual(ret, {'_href': '/base/uri/repo1/'})

    @mock.patch('pulp.server.webservices.http.extend_uri_path', return_value='/base/uri/foo/bar/')
    def test_child_link_obj(self, mock_path):
        ret = link.child_link_obj('foo', 'bar')
        self.assertEqual(ret, {'_href': '/base/uri/foo/bar/'})

    def test_link_dict(self):
        ret = link.link_dict()
        self.assertEqual(ret, {'_href': None})

    def test_link_obj(self):
        ret = link.link_obj('/base/uri/repo1/')
        self.assertEqual(ret, {'_href': '/base/uri/repo1/'})
