# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from pulp.bindings.base import PulpAPI
from pulp.common.compat import json


class OrphanContentAPI(PulpAPI):
    PATH = 'v2/content/orphans/'
    DELETE_BULK_PATH = 'v2/content/actions/delete_orphans/'

    def orphans(self):
        """
        :return: all orphaned content units
        :rtype:  list
        """
        return self.server.GET(self.PATH)

    def orphans_by_type(self, type_id):
        """
        Remove all orphaned units of a specific type
        :param type_id: identifier for a content type
        :type  type_id: str
        """
        path = self.PATH + "%s/" % type_id
        return self.server.GET(path)

    def remove(self, type_id, unit_id):
        """
        Remove a specific orphaned content unit

        :param type_id: id of a content type
        :type  type_id: str
        :param unit_id: id of a content unit
        :type  unit_id: str
        """
        path = self.PATH + '%s/%s/' % (type_id, unit_id)
        return self.server.DELETE(path)

    def remove_bulk(self, specs):
        """
        Remove several orphaned content units.

        :param specs: list of dicts that include keys "content_type_id" and
                      "unit_id". Each dict matches one unit to be removed.
        :type specs:  list of dicts
        """
        expected_keys = set(('content_type_id', 'unit_id'))
        for spec in tuple(specs):
            if not isinstance(spec, dict):
                raise TypeError('members of "spec" must be dicts')
            if expected_keys != set(spec.keys()):
                raise ValueError('dict must include 2 keys: "content_type_id" and "unit_id"')

        body = json.dumps(specs)
        return self.server.POST(self.DELETE_BULK_PATH, body)

    def remove_all(self):
        """
        remove all orphaned content units
        """
        return self.server.DELETE(self.PATH)

    def remove_by_type(self, type_id):
        """
        Remove all orphaned content units of a particular type
        :param type_id: id of a content type
        :type  type_id: str
        """
        path = self.PATH + "%s/" % type_id
        return self.server.DELETE(path)


class ContentSourceAPI(PulpAPI):

    BASE_URL = 'v2/content/sources/'

    def get(self, source_id):
        """
        Get a content source by ID.
        :param source_id: A content source ID.
        :type source_id: str
        :return: The response. The *body* is a content source object.
        :rtype: pulp.bindings.responses.Response
        """
        path = '%s%s/' % (self.BASE_URL, source_id)
        return self.server.GET(path)

    def get_all(self):
        """
        Get all loaded content sources.
        :return: The response. The *body* is a list of content source objects.
        :rtype: pulp.bindings.responses.Response
        """
        path = self.BASE_URL
        return self.server.GET(path)


class ContentCatalogAPI(PulpAPI):

    BASE_URL = 'v2/content/catalog/'

    def delete(self, source_id):
        """
        Delete catalog entries by source ID.
        :param source_id: A content source ID.
        :type source_id: str
        :return: The response.
        :rtype: pulp.bindings.responses.Response
        """
        path = '%s%s/' % (self.BASE_URL, source_id)
        return self.server.DELETE(path)
