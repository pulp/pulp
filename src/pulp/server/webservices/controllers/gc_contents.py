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
        pass

    @error_handler
    @auth_required(CREATE)
    def POST(self):
        """
        Create a new content type.
        """
        pass


class ContentTypeResource(JSONController):

    @error_handler
    @auth_required(DELETE)
    def DELETE(self, type_id):
        """
        Remove a content type.
        """
        pass

    @error_handler
    @auth_required(READ)
    def GET(self, type_id):
        """
        Return information about a content type.
        """
        pass

    @error_handler
    @auth_required(UPDATE)
    def PUT(self, type_id):
        """
        Update a content type.
        """
        pass


class ContentTypeActions(JSONController):

    actions_map = {
        'upload': 'upload_content_unit',
    }

    def upload_content_unit(self, type_id):
        pass

    @error_handler
    @auth_required(EXECUTE)
    def POST(self, type_id, action):
        if action not in self.actions_map:
            return self.not_found(_('Action not defined for %(t)s: %(a)s') %
                                  {'t': type_id, 'a': action})
        method = getattr(self, self.actions_map[action])
        return method(type_id)


class ContentUnitCollection(JSONController):

    @error_handler
    @auth_required(READ)
    def GET(self, type_id):
        """
        List all the available content units.
        """
        pass

    @error_handler
    @auth_required(CREATE)
    def POST(self, type_id):
        """
        Create a new content unit.
        """
        pass


class ContentUnitResource(JSONController):

    @error_handler
    @auth_required(DELETE)
    def DELETE(self, type_id, unit_id):
        """
        Remove a content unit.
        """
        pass

    @error_handler
    @auth_required(READ)
    def GET(self, type_id, unit_id):
        """
        Return information about a content unit.
        """
        pass

    @error_handler
    @auth_required(CREATE)
    def PUT(self, type_id, unit_id):
        """
        Update a content unit.
        """
        pass

# wsgi application -------------------------------------------------------------

_URLS = ('/$', ContentCollections,
         '([^/]+)/$', ContentTypeResource,
         '([^/]+)/actions/(%s)/$' % '|'.join(ContentTypeActions.actions_map), ContentTypeActions,
         '([^/]+)/units/$', ContentUnitCollection,
         '([^/]+)/units/([^/]+)/$', ContentUnitResource,)

application = web.application(_URLS, globals())
