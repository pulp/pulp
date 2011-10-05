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
from pulp.server.webservices import http
from pulp.server.webservices import serialization
from pulp.server.managers.content.exception import ContentUnitNotFound
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required

# controller classes -----------------------------------------------------------

class ContentCollections(JSONController):

    @auth_required(READ)
    def GET(self):
        """
        List the available content types.
        """
        collection = []
        cqm = factory.content_query_manager()
        type_ids = cqm.list_content_types()
        for id in type_ids:
            link = serialization.link.child_link_obj(id)
            link.update({'content_type': id})
            collection.append(link)
        return self.ok(collection)

    def OPTIONS(self):
        link = serialization.link.current_link_obj()
        link.update({'methods': ['GET', 'POST']})
        return self.ok(link)

    @auth_required(CREATE)
    def POST(self):
        """
        Create a new content type.
        """
        return self.not_implemented()


class ContentTypeResource(JSONController):

    @auth_required(DELETE)
    def DELETE(self, type_id):
        """
        Remove a content type.
        """
        return self.not_implemented()

    @auth_required(READ)
    def GET(self, type_id):
        """
        Return information about a content type.
        """
        cqm = factory.content_query_manager()
        content_type = cqm.get_content_type(type_id)
        if content_type is None:
            return self.not_found(_('No content type resource: %(r)s') %
                                  {'r': type_id})
        resource = serialization.content.content_type_obj(content_type)
        links = {'actions': serialization.link.child_link_obj('actions'),
                 'content_units': serialization.link.child_link_obj('units')}
        resource.update(links)
        return self.ok(resource)

    def OPTIONS(self, type_id):
        link = serialization.link.current_link_obj()
        link.update({'methods': ['DELETE', 'GET', 'PUT']})
        return self.ok(link)

    @auth_required(UPDATE)
    def PUT(self, type_id):
        """
        Update a content type.
        """
        return self.not_implemented()


class ContentTypeActionsCollection(JSONController):

    @auth_required(READ)
    def GET(self, type_id):
        collection = []
        for action in ContentTypeActionResource.actions_map:
            link = serialization.link.child_link_obj(action)
            link.update({'action': action})
            # NOTE would be cool to add the POST parameters here
            collection.append(link)
        return self.ok(collection)

    def OPTIONS(self, type_id):
        link = serialization.link.current_link_obj()
        link.update({'methods': ['GET']})
        return self.ok(link)


class ContentTypeActionResource(JSONController):

    actions_map = {
        'upload': 'upload_content_unit',
    }

    # XXX currently unimplemented
    def _upload_content_unit(self, type_id):
        pass

    def OPTIONS(self, type_id, action):
        link = serialization.link.current_link_obj()
        link.update({'methods': ['POST']})
        return self.ok(link)

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

    @auth_required(READ)
    def GET(self, type_id):
        """
        List all the available content units.
        """
        collection = []
        cqm = factory.content_query_manager()
        content_units = cqm.list_content_units(type_id)
        for unit in content_units:
            resource = serialization.content.content_unit_obj(unit)
            resource.update(serialization.link.child_link_obj(unit['id']))
            resource.update({'children': serialization.content.content_unit_child_link_objs(resource)})
            collection.append(resource)
        return self.ok(collection)

    def OPTIONS(self, type_id):
        link = serialization.link.current_link_obj()
        link.update({'methods': ['GET', 'POST']})
        return self.ok(link)

    @auth_required(CREATE)
    def POST(self, type_id):
        """
        Create a new content unit.
        """
        return self.not_implemented()


class ContentUnitResource(JSONController):

    @auth_required(DELETE)
    def DELETE(self, type_id, unit_id):
        """
        Remove a content unit.
        """
        return self.not_implemented()

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
        resource = serialization.content.content_unit_obj(unit)
        resource.update({'children': serialization.content.content_unit_child_link_objs(resource)})
        return self.ok(resource)

    def OPTIONS(self, type_id, unit_id):
        link = serialization.link.current_link_obj()
        link.update({'methods': ['DELETE', 'GET', 'PUT']})
        return self.ok(link)

    @auth_required(CREATE)
    def PUT(self, type_id, unit_id):
        """
        Update a content unit.
        """
        return self.not_implemented()

# wsgi application -------------------------------------------------------------

_URLS = ('/$', ContentCollections,
         '/([^/]+)/$', ContentTypeResource,
         '/([^/]+)/actions/$', ContentTypeActionsCollection,
         '/([^/]+)/actions/(%s)/$' % '|'.join(ContentTypeActionResource.actions_map), ContentTypeActionResource,
         '/([^/]+)/units/$', ContentUnitsCollection,
         '/([^/]+)/units/([^/]+)/$', ContentUnitResource,)

application = web.application(_URLS, globals())
