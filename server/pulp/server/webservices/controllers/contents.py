# -*- coding: utf-8 -*-
#
# Copyright © 2011-2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software;
# if not, see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

from gettext import gettext as _

import web
from web.webapi import BadRequest

from pulp.common import tags
from pulp.server.auth.authorization import CREATE, READ, UPDATE, DELETE
from pulp.server.db.model.criteria import Criteria
from pulp.server.exceptions import MissingResource, InvalidValue, OperationPostponed
from pulp.server.managers import factory
from pulp.server.webservices import serialization
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required
from pulp.server.webservices.controllers.search import SearchController
from pulp.server.managers.content import orphan
from pulp.server.content.sources.container import ContentContainer
from pulp.server.tasks import content
from pulp.common.tags import (action_tag, resource_tag, RESOURCE_CONTENT_SOURCE,
                              ACTION_REFRESH_ALL_CONTENT_SOURCES, ACTION_REFRESH_CONTENT_SOURCE)


class ContentTypesCollection(JSONController):

    @auth_required(READ)
    def GET(self):
        """
        List the available content types.
        """
        collection = []
        cqm = factory.content_query_manager()
        type_ids = cqm.list_content_types()
        for type_id in type_ids:
            link = serialization.link.child_link_obj(type_id)
            link.update({'content_type': type_id})
            collection.append(link)
        return self.ok(collection)


class ContentTypeResource(JSONController):

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


class ContentUnitsCollection(JSONController):

    @staticmethod
    def process_unit(unit):
        unit = serialization.content.content_unit_obj(unit)
        unit.update(serialization.link.search_safe_link_obj(unit['_id']))
        unit.update({'children': serialization.content.content_unit_child_link_objs(unit)})
        return unit

    @auth_required(READ)
    def GET(self, type_id):
        """
        List all the available content units.
        """
        cqm = factory.content_query_manager()
        units = cqm.find_by_criteria(type_id, Criteria())
        return self.ok([self.process_unit(unit) for unit in units])


class ContentUnitsSearch(SearchController):
    def __init__(self):
        super(ContentUnitsSearch, self).__init__(self._proxy_query_method)

    def _proxy_query_method(self, criteria):
        """
        Normally the constructor passes a manager's query method to the
        super-class constructor. Since our manager's query method takes an extra
        parameter to tell it what content type to look in, we have this proxy
        query method that will make the correct call at the time.

        Also, at the time of instantiation, we don't know what the content
        type_id will be, so each request handler method will set self._type_id
        to the correct value, and this method will use it at the time of being
        called.

        This sounds like it's asking for a race condition, I know, but web.py
        instantiates a new controller for each and every request, so that isn't
        a concern.

        @param criteria:    Criteria representing a search
        @type  criteria:    models.db.criteria.Criteria

        @return:    same as PulpCollection.query
        """
        return factory.content_query_manager().find_by_criteria(
            self._type_id, criteria)

    @staticmethod
    def _add_repo_memberships(units, type_id):
        """
        For a list of units, find what repos each is a member of, and add a list
        of repo_ids to each unit.

        :param units:   list of unit documents
        :type  units:   list of dicts
        :param type_id: content type id
        :type  type_id: str
        :return:    same list of units that was passed in, only for convenience.
                    units are modified in-place
        """
        # quick return if there is nothing to do
        if not units:
            return units

        unit_ids = [unit['_id'] for unit in units]
        criteria = Criteria(
            filters={'unit_id': {'$in': unit_ids}, 'unit_type_id': type_id},
            fields=('repo_id', 'unit_id')
        )
        associations = factory.repo_unit_association_query_manager().find_by_criteria(criteria)
        unit_ids = None
        criteria = None
        association_map = {}
        for association in associations:
            association_map.setdefault(association['unit_id'], set()).add(
                association['repo_id'])

        for unit in units:
            unit['repository_memberships'] = list(association_map.get(unit['_id'], []))
        return units

    @auth_required(READ)
    def GET(self, type_id):
        """
        Does a normal GET after setting the query method from the appropriate
        PulpCollection.

        Include query parameter "repos" with any value that evaluates to True to
        get the attribute "repository_memberships" added to each unit.

        @param type_id: id of a ContentType that we are searching.
        @type  type_id: basestring
        """
        self._type_id = type_id
        raw_units = self._get_query_results_from_get(ignore_fields=('include_repos',))
        units = [ContentUnitsCollection.process_unit(unit) for unit in raw_units]
        if web.input().get('include_repos'):
            self._add_repo_memberships(units, type_id)

        return self.ok(units)

    @auth_required(READ)
    def POST(self, type_id):
        """
        Does a normal POST after setting the query method from the appropriate
        PulpCollection.

        In the body, include key "repos" with any value that evaluates to True
        to get the attribute "repository_memberships" added to each unit.

        @param type_id: id of a ContentType that we are searching.
        @type  type_id: basestring
        """
        self._type_id = type_id
        raw_units = self._get_query_results_from_post()
        units = [ContentUnitsCollection.process_unit(unit) for unit in raw_units]
        if self.params().get('include_repos'):
            self._add_repo_memberships(units, type_id)

        return self.ok(units)


class ContentUnitResource(JSONController):

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

# content uploads controller classes -------------------------------------------


class UploadsCollection(JSONController):

    # Scope: Collection
    # GET:   Retrieve all upload request IDs
    # POST:  Create a new upload request (and return the ID)

    @auth_required(READ)
    def GET(self):
        upload_manager = factory.content_upload_manager()
        upload_ids = upload_manager.list_upload_ids()

        return self.ok({'upload_ids': upload_ids})

    @auth_required(CREATE)
    def POST(self):
        upload_manager = factory.content_upload_manager()
        upload_id = upload_manager.initialize_upload()
        location = serialization.link.child_link_obj(upload_id)
        return self.created(location['_href'], {'_href': location['_href'], 'upload_id': upload_id})


class UploadResource(JSONController):

    # Scope:  Resource
    # DELETE: Delete an uploaded file

    @auth_required(DELETE)
    def DELETE(self, upload_id):
        upload_manager = factory.content_upload_manager()
        upload_manager.delete_upload(upload_id)

        return self.ok(None)


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

        return self.ok(None)


class OrphanCollection(JSONController):

    @auth_required(READ)
    def GET(self):
        orphan_manager = factory.content_orphan_manager()
        summary = orphan_manager.orphans_summary()
        # convert the counts into sub-documents so we can add _href fields to them
        rest_summary = dict((k, {'count': v}) for k, v in summary.items())
        # add links to the content type sub-collections
        map(lambda k: rest_summary[k].update(serialization.link.child_link_obj(k)), rest_summary)
        return self.ok(rest_summary)

    @auth_required(DELETE)
    def DELETE(self):
        task_tags = [tags.resource_tag(tags.RESOURCE_CONTENT_UNIT_TYPE, 'orphans')]
        async_task = orphan.delete_all_orphans.apply_async(tags=task_tags)
        raise OperationPostponed(async_task)


class OrphanTypeSubCollection(JSONController):

    @auth_required(READ)
    def GET(self, content_type):
        orphan_manager = factory.content_orphan_manager()
        # NOTE this can still potentially stomp on memory, but hopefully the
        # _with_unit_keys methods will reduce the foot print enough that
        # we'll never see this bug again
        orphans = list(orphan_manager.generate_orphans_by_type_with_unit_keys(content_type))
        map(lambda o: o.update(serialization.link.child_link_obj(o['_id'])), orphans)
        return self.ok(orphans)

    @auth_required(DELETE)
    def DELETE(self, content_type):
        task_tags = [tags.resource_tag(tags.RESOURCE_CONTENT_UNIT_TYPE, 'orphans')]
        async_task = orphan.delete_orphans_by_type.apply_async((content_type,), tags=task_tags)
        raise OperationPostponed(async_task)


class OrphanResource(JSONController):

    @auth_required(READ)
    def GET(self, content_type, content_id):
        orphan_manager = factory.content_orphan_manager()
        orphan = orphan_manager.get_orphan(content_type, content_id)
        orphan.update(serialization.link.current_link_obj())
        return self.ok(orphan)

    @auth_required(DELETE)
    def DELETE(self, content_type, content_id):
        ids = [{'content_type_id': content_type, 'unit_id': content_id}]
        task_tags = [tags.resource_tag(tags.RESOURCE_CONTENT_UNIT_TYPE, 'orphans')]
        async_task = orphan.delete_orphans_by_id.apply_async((ids,), tags=task_tags)
        raise OperationPostponed(async_task)


class DeleteOrphansAction(JSONController):
    # deprecated in 2.4, please use the more restful OrphanResource delete instead
    @auth_required(DELETE)
    def POST(self):
        orphans = self.params()
        task_tags = [tags.action_tag('delete_orphans'),
                tags.resource_tag(tags.RESOURCE_CONTENT_UNIT_TYPE, 'orphans')]
        async_task = orphan.delete_orphans_by_id.apply_async([orphans], tags=task_tags)
        raise OperationPostponed(async_task)


class CatalogResource(JSONController):

    @auth_required(DELETE)
    def DELETE(self, source_id):
        manager = factory.content_catalog_manager()
        purged = manager.purge(source_id)
        deleted = dict(deleted=purged)
        return self.ok(deleted)


class ContentSourceCollection(JSONController):

    @auth_required(READ)
    def GET(self):
        """
        Get all content sources.
        :return: List of sources.
        :rtype: list
        """
        container = ContentContainer()
        sources = []
        for source in container.sources.values():
            d = source.dict()
            href = serialization.link.child_link_obj(source.id)
            d.update(href)
            sources.append(d)
        return self.ok(sources)

    @auth_required(UPDATE)
    def POST(self, action):
        """
        Content source actions.
        :param action: Name of action to perform
        :type action: str
        """
        method = getattr(self, action, None)
        if method:
            return method()
        else:
            raise BadRequest()

    def refresh(self):
        """
        Refresh all content sources

        """
        container = ContentContainer()
        content_sources = [resource_tag(RESOURCE_CONTENT_SOURCE, id)
                           for id in container.sources.keys()]
        tags = [action_tag(ACTION_REFRESH_ALL_CONTENT_SOURCES)] + content_sources
        task_result = content.refresh_content_sources.apply_async(tags=tags)
        raise OperationPostponed(task_result)


class ContentSourceResource(JSONController):

    @auth_required(READ)
    def GET(self, source_id):
        """
        Get a content source by ID.
        :param source_id: A content source ID.
        :type source_id: str
        :return: A content source object.
        :rtype: dict
        """
        container = ContentContainer()
        source = container.sources.get(source_id)
        if source:
            return self.ok(source.dict())
        else:
            raise MissingResource(source_id=source_id)

    @auth_required(UPDATE)
    def POST(self, source_id, action):
        """
        Content source actions.
        """
        container = ContentContainer()
        source = container.sources.get(source_id)
        if source:
            method = getattr(self, action, None)
            if method:
                return method(source_id)
            else:
                raise BadRequest()
        else:
            raise MissingResource(source_id=source_id)

    def refresh(self, content_source_id):
        """
        Refresh content source
        :param content_source_id: A content source ID
        :type content_source_id: str
        :return 202
        :rtype
        """
        tags = [action_tag(ACTION_REFRESH_CONTENT_SOURCE), resource_tag(RESOURCE_CONTENT_SOURCE,content_source_id)]
        task_result = content.refresh_content_source.apply_async(tags=tags, kwargs={'content_source_id':content_source_id})
        raise OperationPostponed(task_result)


# wsgi application -------------------------------------------------------------

_URLS = ('/types/$', ContentTypesCollection,
         '/types/([^/]+)/$', ContentTypeResource,
         '/units/([^/]+)/$', ContentUnitsCollection,
         '/units/([^/]+)/search/$', ContentUnitsSearch,
         '/units/([^/]+)/([^/]+)/$', ContentUnitResource,
         '/uploads/$', UploadsCollection,
         '/uploads/([^/]+)/$', UploadResource,
         '/uploads/([^/]+)/([^/]+)/$', UploadSegmentResource,
         '/orphans/$', OrphanCollection,
         '/orphans/([^/]+)/$', OrphanTypeSubCollection,
         '/orphans/([^/]+)/([^/]+)/$', OrphanResource,
         '/actions/delete_orphans/$', DeleteOrphansAction,  # deprecated in 2.4
         '/catalog/([^/]+)$', CatalogResource,  # deprecated in 2.5, missing trailing '/'
         '/catalog/([^/]+)/$', CatalogResource,
         '/sources/$', ContentSourceCollection,
         '/sources/action/(refresh)/$', ContentSourceCollection,
         '/sources/([^/]+)/$', ContentSourceResource,
         '/sources/([^/]+)/action/([^/]+)/$', ContentSourceResource)

application = web.application(_URLS, globals())
