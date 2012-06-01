# -*- coding: utf-8 -*-
#
# Copyright © 2011-2012 Red Hat, Inc.
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

from pulp.common.tags import action_tag, resource_tag
from pulp.server.auth.authorization import CREATE, READ, UPDATE, DELETE, EXECUTE
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch.call import CallRequest
from pulp.server.exceptions import MissingResource, InvalidValue
from pulp.server.managers import factory
from pulp.server.webservices import execution, serialization
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required

# content types controller classes ---------------------------------------------

class ContentTypesCollection(JSONController):

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

# content units controller classes ---------------------------------------------

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
            resource.update(serialization.link.child_link_obj(unit['_id']))
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
        except MissingResource:
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

# content uploads controller classes -------------------------------------------

class UploadsCollection(JSONController):

    # Scope: Collection
    # GET:   Retrieve all upload request IDs
    # POST:  Create a new upload request (and return the ID)

    @auth_required(READ)
    def GET(self):
        upload_manager = factory.content_upload_manager()
        upload_ids = upload_manager.list_upload_ids()

        return self.ok({'upload_ids' : upload_ids})

    @auth_required(CREATE)
    def POST(self):
        upload_manager = factory.content_upload_manager()
        upload_id = upload_manager.initialize_upload()
        location = serialization.link.child_link_obj(upload_id)
        return self.created(location['_href'], {'_href' : location['_href'], 'upload_id' : upload_id})

class UploadResource(JSONController):

    # Scope:  Resource
    # DELETE: Delete an uploaded file

    @auth_required(DELETE)
    def DELETE(self, upload_id):
        upload_manager = factory.content_upload_manager()
        upload_manager.delete_upload(upload_id)

        return self.ok({})

class UploadSegmentResource(JSONController):

    # Scope: Sub-Resource
    # PUT:   Upload bits into a file upload

    @auth_required(UPDATE)
    def PUT(self, upload_id, offset):

        # If the upload ID doesn't exists, either because it was not initialized
        # or was deleted, the call to the manager will raise missing resource

        try:
            offset = int(offset)
        except ValueError:
            raise InvalidValue(['offset'])

        upload_manager = factory.content_upload_manager()
        data = self.data()
        upload_manager.save_data(upload_id, offset, data)

        return self.ok({})

# content orphans controller classes -------------------------------------------

class OrphanCollection(JSONController):

    @auth_required(READ)
    def GET(self):
        orphan_manager = factory.content_orphan_manager()
        orphans = orphan_manager.list_all_orphans()
        map(lambda o: o.update(serialization.link.child_link_obj(o['_content_type_id'], o['_id'])), orphans)
        return self.ok(orphans)

    @auth_required(DELETE)
    def DELETE(self):
        orphan_manager = factory.content_orphan_manager()
        tags = [resource_tag(dispatch_constants.RESOURCE_CONTENT_UNIT_TYPE, 'orphans')]
        call_request = CallRequest(orphan_manager.delete_all_orphans, tags=tags, archive=True)
        return execution.execute_async(self, call_request)


class OrphanTypeSubCollection(JSONController):

    @auth_required(READ)
    def GET(self, content_type):
        orphan_manager = factory.content_orphan_manager()
        orphans = orphan_manager.list_orphans_by_type(content_type)
        map(lambda o: o.update(serialization.link.child_link_obj(o['_id'])), orphans)
        return self.ok(orphans)

    @auth_required(DELETE)
    def DELETE(self, content_type):
        orphan_manager = factory.content_orphan_manager()
        tags = [resource_tag(dispatch_constants.RESOURCE_CONTENT_UNIT_TYPE, 'orphans')]
        call_request = CallRequest(orphan_manager.delete_orphans_by_type, [content_type], tags=tags, archive=True)
        return execution.execute_async(self, call_request)

class OrphanResource(JSONController):

    @auth_required(READ)
    def GET(self, content_type, content_id):
        orphan_manager = factory.content_orphan_manager()
        orphan = orphan_manager.get_orphan(content_type, content_id)
        orphan.update(serialization.link.current_link_obj())
        return self.ok(orphan)

    @auth_required(DELETE)
    def DELETE(self, content_type, content_id):
        orphan_manager = factory.content_orphan_manager()
        orphan_manager.get_orphan(content_type, content_id)
        ids = [{'content_type_id': content_type, 'unit_id': content_id}]
        tags = [resource_tag(dispatch_constants.RESOURCE_CONTENT_UNIT_TYPE, 'orphans')]
        call_request = CallRequest(orphan_manager.delete_orphans_by_id, [ids], tags=tags, archive=True)
        return execution.execute_async(self, call_request)

# content actions controller classes -------------------------------------------

class DeleteOrphansAction(JSONController):

    @auth_required(DELETE)
    def POST(self):
        orphans = self.params()
        orphan_manager = factory.content_orphan_manager()
        tags = [action_tag('delete_orphans'),
                resource_tag(dispatch_constants.RESOURCE_CONTENT_UNIT_TYPE, 'orphans')]
        call_request = CallRequest(orphan_manager.delete_orphans_by_id, [orphans], tags=tags, archive=True)
        return execution.execute_async(self, call_request)

# wsgi application -------------------------------------------------------------

_URLS = ('/types/$', ContentTypesCollection,
         '/types/([^/]+)/$', ContentTypeResource,
         '/units/([^/]+)/$', ContentUnitsCollection,
         '/units/([^/]+)/([^/]+)/$', ContentUnitResource,
         '/uploads/$', UploadsCollection,
         '/uploads/([^/]+)/$', UploadResource,
         '/uploads/([^/]+)/([^/]+)/$', UploadSegmentResource,
         '/orphans/$', OrphanCollection,
         '/orphans/([^/]+)/$', OrphanTypeSubCollection,
         '/orphans/([^/]+)/([^/]+)/$', OrphanResource,
         '/actions/delete_orphans/$', DeleteOrphansAction,)

application = web.application(_URLS, globals())
