# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including implied
# warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR
# PURPOSE. You should have received a copy of GPLv2 along with this software;
# if not, see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import unittest

import mock

from pulp.bindings.content import OrphanContentAPI, ContentSourceAPI, ContentCatalogAPI
from pulp.common.compat import json


class TestOrphanAPI(unittest.TestCase):
    def setUp(self):
        self.api = OrphanContentAPI(mock.MagicMock())

    def test_paths(self):
        self.assertTrue(len(self.api.PATH) > 0)
        # make sure it's a relative path
        self.assertFalse(self.api.PATH.startswith('/'))

    def test_delete_bulk_path(self):
        self.assertTrue(len(self.api.DELETE_BULK_PATH) > 0)
        # make sure it's a relative path
        self.assertFalse(self.api.DELETE_BULK_PATH.startswith('/'))

    def test_list_orphans(self):
        ret = self.api.orphans()

        self.api.server.GET.assert_called_once_with(self.api.PATH)
        self.assertEqual(ret, self.api.server.GET.return_value)

    def test_list_orphans_by_type(self):
        ret = self.api.orphans_by_type('rpm')

        self.api.server.GET.assert_called_once_with(self.api.PATH + 'rpm/')
        self.assertEqual(ret, self.api.server.GET.return_value)

    def test_remove(self):
        ret = self.api.remove('rpm', 'foo')

        self.api.server.DELETE.assert_called_once_with(self.api.PATH + 'rpm/foo/')
        self.assertEqual(ret, self.api.server.DELETE.return_value)

    def test_remove_by_type(self):
        ret = self.api.remove_by_type('rpm')

        self.api.server.DELETE.assert_called_once_with(self.api.PATH + 'rpm/')
        self.assertEqual(ret, self.api.server.DELETE.return_value)

    def test_remove_all(self):
        ret = self.api.remove_all()

        self.api.server.DELETE.assert_called_once_with(self.api.PATH)
        self.assertEqual(ret, self.api.server.DELETE.return_value)


class TestRemoveBulk(unittest.TestCase):
    def setUp(self):
        self.api = OrphanContentAPI(mock.MagicMock())

    def test_spec_not_iterable(self):
        self.assertRaises(TypeError, self.api.remove_bulk, 123)

    def test_members_not_dicts(self):
        self.assertRaises(TypeError, self.api.remove_bulk, ['abc', 'def'])

    def test_dicts_missing_keys(self):
        self.assertRaises(ValueError, self.api.remove_bulk, [{}, {}])

    def test_dicts_have_extra_keys(self):
        self.assertRaises(ValueError, self.api.remove_bulk,
            [{'content_type_id' : 'foo', 'unit_id' : 'bar', 'x' : 'y'}])

    def test_success(self):
        specs = [{'content_type_id' : 'foo', 'unit_id' : 'bar'}]
        ret = self.api.remove_bulk(specs)

        body = json.dumps(specs)
        self.api.server.POST.assert_called_once_with(self.api.DELETE_BULK_PATH,
        body)

        self.assertEqual(ret, self.api.server.POST.return_value)


class TestContentSources(unittest.TestCase):

    def test_get_all(self):
        connection = mock.Mock()
        api = ContentSourceAPI(connection)

        # test
        body = api.get_all()

        # validation
        connection.GET.assert_called_once_with(ContentSourceAPI.BASE_URL)
        self.assertEqual(body, connection.GET.return_value)

    def test_get(self):
        source_id = 'test-id'
        connection = mock.Mock()
        api = ContentSourceAPI(connection)

        # test
        body = api.get(source_id)

        # validation
        path = '%s%s/' % (ContentSourceAPI.BASE_URL, source_id)
        connection.GET.assert_called_once_with(path)
        self.assertEqual(body, connection.GET.return_value)


class TestCatalog(unittest.TestCase):

    def test_delete(self):
        source_id = 'content-world'
        connection = mock.Mock()
        api = ContentCatalogAPI(connection)

        # test
        body = api.delete(source_id)

        # validation
        path = '%s%s/' % (ContentCatalogAPI.BASE_URL, source_id)
        connection.DELETE.assert_called_once_with(path)
        self.assertEqual(body, connection.DELETE.return_value)
