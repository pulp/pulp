from web.webapi import BadRequest
import web

from pulp.server.auth.authorization import CREATE, READ, UPDATE
from pulp.server.content.sources.container import ContentContainer
from pulp.server.db.model.criteria import Criteria
from pulp.server.exceptions import MissingResource, OperationPostponed
from pulp.server.managers import factory
from pulp.common.tags import (action_tag, resource_tag, RESOURCE_CONTENT_SOURCE,
                              ACTION_REFRESH_ALL_CONTENT_SOURCES, ACTION_REFRESH_CONTENT_SOURCE)
from pulp.server.tasks import content
from pulp.server.webservices import serialization
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required
from pulp.server.webservices.controllers.search import SearchController


class ContentUnitsCollection(JSONController):

    # Left here because this method is is used by other classes in this module.
    @staticmethod
    def process_unit(unit):
        unit = serialization.content.content_unit_obj(unit)
        unit.update(serialization.link.search_safe_link_obj(unit['_id']))
        unit.update({'children': serialization.content.content_unit_child_link_objs(unit)})
        return unit


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
        tags = [action_tag(ACTION_REFRESH_CONTENT_SOURCE),
                resource_tag(RESOURCE_CONTENT_SOURCE, content_source_id)]
        task_result = content.refresh_content_source.apply_async(
            tags=tags, kwargs={'content_source_id': content_source_id})
        raise OperationPostponed(task_result)


_URLS = ('/units/([^/]+)/search/$', ContentUnitsSearch,
         '/uploads/$', UploadsCollection,
         '/sources/$', ContentSourceCollection,
         '/sources/action/(refresh)/$', ContentSourceCollection,
         '/sources/([^/]+)/$', ContentSourceResource,
         '/sources/([^/]+)/action/([^/]+)/$', ContentSourceResource)

application = web.application(_URLS, globals())
