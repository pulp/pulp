# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from gettext import gettext as _

import web

from pulp.server.auth.authorization import (
    CREATE, READ, UPDATE, DELETE, EXECUTE)
from pulp.server.managers import factory
from pulp.server.managers.content.exception import ContentUnitNotFound
from pulp.server.webservices import http
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import (
    auth_required, error_handler)

# controller classes -----------------------------------------------------------

class ContentCollections(JSONController):

    @error_handler
    @auth_required(READ)
    def GET(self):
        """
        List the available content types.
        """
        collection = {'href': http.uri_path(),
                      'content_types': []}
        cqm = factory.content_query_manager()
        type_ids = cqm.list_content_types()
        for id in type_ids:
            link = {'type_id': id,
                    'href': http.extend_uri_path(id)}
            collection['content_types'].append(link)
        return self.ok(collection)

    @error_handler
    def OPTIONS(self):
        options = {'href': http.uri_path(),
                   'methods': ['GET', 'POST']}
        return self.ok(options)

    @error_handler
    @auth_required(CREATE)
    def POST(self):
        """
        Create a new content type.
        """
        return self.not_implemented()


class ContentTypeResource(JSONController):

    @error_handler
    @auth_required(DELETE)
    def DELETE(self, type_id):
        """
        Remove a content type.
        """
        return self.not_implemented()

    @error_handler
    @auth_required(READ)
    def GET(self, type_id):
        """
        Return information about a content type.
        """
        cqm = factory.content_query_manager()
        type_ = cqm.get_content_type(type_id)
        if type_ is None:
            return self.not_found(_('No content type resource: %(r)s') %
                                  {'r': type_id})
        resource = {'href': http.uri_path(),
                    'actions': {'href': http.extend_uri_path('actions')},
                    'content_units': {'href': http.extend_uri_path('units')},
                    'content_type': type_}
        return self.ok(resource)

    @error_handler
    def OPTIONS(self, type_id):
        options = {'href': http.uri_path(),
                   'methods': ['DELETE', 'GET', 'PUT']}
        return self.ok(options)

    @error_handler
    @auth_required(UPDATE)
    def PUT(self, type_id):
        """
        Update a content type.
        """
        return self.not_implemented()


class ContentTypeActionsCollection(JSONController):

    @error_handler
    @auth_required(READ)
    def GET(self, type_id):
        collection = {'href': http.uri_path(),
                      'actions': []}
        for action in ContentTypeActionResource.actions_map:
            link = {'action': action,
                    'href': http.extend_uri_path(action)}
            collection['actions'].append(link)
        return self.ok(collection)

    @error_handler
    def OPTIONS(self, type_id):
        options = {'href': http.uri_path(),
                   'methods': ['GET']}
        return self.ok(options)


class ContentTypeActionResource(JSONController):

    actions_map = {
        'upload': 'upload_content_unit',
    }

    # XXX currently unimplemented
    def _upload_content_unit(self, type_id):
        pass

    @error_handler
    def OPTIONS(self, type_id, action):
        options = {'href': http.uri_path(),
                   'methods': ['POST']}
        return self.ok(options)

    @error_handler
    @auth_required(EXECUTE)
    def POST(self, type_id, action):
        if action not in self.actions_map:
            return self.not_found(_('Action not defined for %(t)s: %(a)s') %
                                  {'t': type_id, 'a': action})
        method = getattr(self, self.actions_map[action], None)
        if method is None:
            return self.not_implemented(_('Action not implemented for %(t)s: %(a)s') %
                                        {'t': type_id, 'a': action})
        return method(type_id)


class ContentUnitsCollection(JSONController):

    @error_handler
    @auth_required(READ)
    def GET(self, type_id):
        """
        List all the available content units.
        """
        collection = {'href': http.uri_path(),
                      'content_units': []}
        cqm = factory.content_query_manager()
        content_units = cqm.list_content_units(type_id)
        for unit in content_units:
            link = {'href': http.extend_uri_path(unit['id']),
                    'content_unit': unit}
            collection['content_units'].append(link)
        return self.ok(collection)

    @error_handler
    def OPTIONS(self, type_id):
        options = {'href': http.uri_path(),
                   'methods': ['GET', 'POST']}
        return self.ok(options)

    @error_handler
    @auth_required(CREATE)
    def POST(self, type_id):
        """
        Create a new content unit.
        """
        return self.not_implemented()


class ContentUnitResource(JSONController):

    @error_handler
    @auth_required(DELETE)
    def DELETE(self, type_id, unit_id):
        """
        Remove a content unit.
        """
        return self.not_implemented()

    @error_handler
    @auth_required(READ)
    def GET(self, type_id, unit_id):
        """
        Return information about a content unit.
        """
        cqm = factory.content_query_manager()
        try:
            unit = cqm.get_content_unit_by_id(type_id, unit_id)
        except ContentUnitNotFound:
            return self.not_found(_('No content unit resource: %(r)s') %
                                  {'r': unit_id})
        resource = {'href': http.uri_path(),
                    'content_unit': unit}
        return self.ok(resource)

    @error_handler
    def OPTIONS(self, type_id, unit_id):
        options = {'href': http.uri_path(),
                   'methods': ['DELETE', 'GET', 'PUT']}
        return self.ok(options)

    @error_handler
    @auth_required(CREATE)
    def PUT(self, type_id, unit_id):
        """
        Update a content unit.
        """
        return self.not_implemented()

# wsgi application -------------------------------------------------------------

_URLS = ('/$', ContentCollections,
         '([^/]+)/$', ContentTypeResource,
         '([^/]+)/actions/$', ContentTypeActionsCollection,
         '([^/]+)/actions/(%s)/$' % '|'.join(ContentTypeActionResource.actions_map), ContentTypeActionResource,
         '([^/]+)/units/$', ContentUnitsCollection,
         '([^/]+)/units/([^/]+)/$', ContentUnitResource,)

application = web.application(_URLS, globals())
