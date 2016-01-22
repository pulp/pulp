from gettext import gettext as _

from django.core.urlresolvers import reverse
from django.http import HttpResponseNotFound, HttpResponseBadRequest
from django.views.generic import View

from pulp.common import tags
from pulp.common.tags import (ACTION_REFRESH_ALL_CONTENT_SOURCES,
                              ACTION_REFRESH_CONTENT_SOURCE,
                              RESOURCE_CONTENT_SOURCE)
from pulp.server import constants
from pulp.server.auth import authorization
from pulp.server.content.sources.container import ContentContainer
from pulp.server.controllers import content
from pulp.server.controllers import units as units_controller
from pulp.server.db.model.criteria import Criteria
from pulp.server.exceptions import InvalidValue, MissingResource, OperationPostponed
from pulp.server.managers import factory
from pulp.server.managers.content import query as content_query
from pulp.server.managers.content import orphan as content_orphan
from pulp.server.webservices.views import search
from pulp.server.webservices.views.decorators import auth_required
from pulp.server.webservices.views.serializers import content as serial_content
from pulp.server.webservices.views.util import (generate_json_response,
                                                generate_json_response_with_pulp_encoder,
                                                generate_redirect_response,
                                                parse_json_body)


def _process_content_unit(content_unit, content_type):
    """
    Adds an href to the content unit and hrefs for its children.

    :param content_unit: content unit to serialize
    :type  content_unit: dict
    :param content_type: type of content_unit
    :type  content_type: str

    :return: serialized unit
    :rtype:  dict
    """
    unit = serial_content.content_unit_obj(content_unit)
    unit['_href'] = reverse(
        'content_unit_resource',
        kwargs={'type_id': content_type, 'unit_id': content_unit['_id']}
    )
    unit.update({'children': serial_content.content_unit_child_link_objs(unit)})
    return unit


class OrphanCollectionView(View):
    """
    Views for all orphans.
    """

    @auth_required(authorization.READ)
    def get(self, request):
        """
        Return a response containing a dict of dicts, one for each orphaned unit.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest

        :return: response containing a dict that itself contains a dict for each orphan.
        :rtype: django.http.HttpResponse
        """
        orphan_manager = factory.content_orphan_manager()

        # convert the counts into sub-documents so we can add _href fields to them
        # add links to the content type sub-collections
        rest_summary = {}
        for key, value in orphan_manager.orphans_summary().items():
            rest_summary[key] = {
                'count': value,
                '_href': reverse('content_orphan_type_subcollection', kwargs={'content_type': key})
            }
        return generate_json_response(rest_summary)

    @auth_required(authorization.DELETE)
    def delete(self, request):
        """
        Dispatch a delete_all_orphans task.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest

        :raises: OperationPostponed when an async operation is performed
        """
        task_tags = [tags.resource_tag(tags.RESOURCE_CONTENT_UNIT_TYPE, 'orphans')]
        async_task = content_orphan.delete_all_orphans.apply_async(tags=task_tags)
        raise OperationPostponed(async_task)


class OrphanTypeSubCollectionView(View):
    """
    Views for orphans of a specific type.
    """

    @auth_required(authorization.READ)
    def get(self, request, content_type):
        """
        Returns a response containing a serialized list of all orphans of the specified type.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param content_type: restrict the list of orphans to this content type
        :type  content_type: str

        :return: response containing a serialized list of all orphans of specified type.
        :rtype : django.http.HttpResponse
        """
        orphan_manager = factory.content_orphan_manager()
        matched_orphans = list(orphan_manager.generate_orphans_by_type_with_unit_keys(content_type))
        for orphan_dict in matched_orphans:
            orphan_dict['_href'] = reverse(
                'content_orphan_resource',
                kwargs={'content_type': content_type, 'unit_id': orphan_dict['_id']}
            )
        return generate_json_response(matched_orphans)

    @auth_required(authorization.DELETE)
    def delete(self, request, content_type):
        """
        Dispatch a delete_orphans_by_type task.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param content_type: restrict the list of orphans to be deleted to this content type
        :type  content_type: str

        :raises: OperationPostponed when an async operation is performed
        :raises: MissingResource when the content type does not exist
        """
        try:
            # this tests if the type exists
            units_controller.get_unit_key_fields_for_type(content_type)
        except ValueError:
            raise MissingResource(content_type_id=content_type)

        task_tags = [tags.resource_tag(tags.RESOURCE_CONTENT_UNIT_TYPE, 'orphans')]
        async_task = content_orphan.delete_orphans_by_type.apply_async(
            (content_type,), tags=task_tags
        )
        raise OperationPostponed(async_task)


class OrphanResourceView(View):
    """
    Views for a specific orphan.
    """
    @auth_required(authorization.READ)
    def get(self, request, content_type, unit_id):
        """
        Return a serialized object representing the requested orphan

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param content_type: content type of the requested orphan
        :type  content_type: str
        :param unit_id: id of the requested unit
        :type  unit_id: str

        :return: response conainting a serialized dict of the requested orphan
        :rtype : django.http.HttpResponse
        """
        orphan_manager = factory.content_orphan_manager()
        orphan_dict = orphan_manager.get_orphan(content_type, unit_id)
        orphan_dict['_href'] = request.get_full_path()
        return generate_json_response(orphan_dict)

    @auth_required(authorization.DELETE)
    def delete(self, request, content_type, unit_id):
        """
        Dispatch a delete_orphans_by_id task.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param content_type: content type of the requested orphan
        :type  content_type: str
        :param unit_id: id of the requested orphan
        :type  unit_id: str

        :raises: OperationPostponed when an async operation is performed
        """
        orphan_manager = factory.content_orphan_manager()
        orphan_manager.get_orphan(content_type, unit_id)
        unit_info = [{'content_type_id': content_type, 'unit_id': unit_id}]
        task_tags = [tags.resource_tag(tags.RESOURCE_CONTENT_UNIT_TYPE, 'orphans')]
        async_task = content_orphan.delete_orphans_by_id.apply_async((unit_info,), tags=task_tags)
        raise OperationPostponed(async_task)


class DeleteOrphansActionView(View):
    """
    Deprecated in 2.4, please use the more restful OrphanResource delete instead

    Delete all orphans.
    """

    @auth_required(authorization.DELETE)
    @parse_json_body(allow_empty=True)
    def post(self, request):
        """
        Dispatch a delete_orphan_by_id task.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest

        :raises: OperationPostponed when an async operation is performed
        """
        all_orphans = request.body_as_json
        task_tags = [tags.action_tag('delete_orphans'),
                     tags.resource_tag(tags.RESOURCE_CONTENT_UNIT_TYPE, 'orphans')]
        async_task = content_orphan.delete_orphans_by_id.apply_async([all_orphans], tags=task_tags)
        raise OperationPostponed(async_task)


class CatalogResourceView(View):
    """
    Views for the catalog by source_id.
    """

    @auth_required(authorization.DELETE)
    def delete(self, request, source_id):
        """
        Delete all entries from the catlog that have the provided source id

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param source_id: id of source whose content should be deleted
        :type  source_id: str

        :return: response containing a dict containing the number if items deleted
        :rtype : django.http.HttpResponse
        """
        manager = factory.content_catalog_manager()
        purged = manager.purge(source_id)
        deleted_info = dict(deleted=purged)
        return generate_json_response(deleted_info)


class ContentUnitSearch(search.SearchView):
    """
    Adds GET and POST searching for content units.
    """
    optional_bool_fields = ('include_repos',)
    manager = content_query.ContentQueryManager()

    @staticmethod
    def _add_repo_memberships(units, type_id):
        """
        For a list of units, find what repos each is a member of and add a list
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

    @classmethod
    def get_results(cls, query, search_method, options, *args, **kwargs):
        """
        Overrides the base class so additional information can optionally be added.
        """

        type_id = kwargs['type_id']
        serializer = units_controller.get_model_serializer_for_type(type_id)
        if serializer:
            # if we have a model serializer, translate the filter for this content unit type
            query['filters'] = serializer.translate_filters(serializer.model, query['filters'])
        units = list(search_method(type_id, query))
        units = [_process_content_unit(unit, type_id) for unit in units]
        if options.get('include_repos') is True:
            cls._add_repo_memberships(units, type_id)
        return units


class ContentUnitResourceView(View):
    """
    View for individual content units.
    """

    @auth_required(authorization.READ)
    def get(self, request, type_id, unit_id):
        """
        Return a response containing information about the requested content unit.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param type_id: type of content contained in the repo
        :type  type_id: str
        :param unit_id: unique id of a unit
        :type  unit_id: str

        :return: response containing a dict with data about requested unit
        :rtype : django.http.HttpResponse
        """
        cqm = factory.content_query_manager()
        try:
            unit = cqm.get_content_unit_by_id(type_id, unit_id)
        except MissingResource:
            msg = _('No content unit resource: %(r)s') % {'r': unit_id}
            return generate_json_response(msg, response_class=HttpResponseNotFound)

        resource = serial_content.content_unit_obj(unit)
        resource.update({'children': serial_content.content_unit_child_link_objs(resource)})
        return generate_json_response_with_pulp_encoder(resource)


class ContentUnitsCollectionView(View):
    """
    View for all content units of a specified type.
    """

    @auth_required(authorization.READ)
    def get(self, request, type_id):
        """
        Return a response with a serialized list of the content units of the specified type.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param type_id: the list of content units will be limited to this type
        :type  type_id: str

        :return: response with a serialized list of dicts, one for each unit of the type.
        :rtype: django.http.HttpResponse
        """
        cqm = factory.content_query_manager()
        all_units = cqm.find_by_criteria(type_id, Criteria())
        all_processed_units = [_process_content_unit(unit, type_id) for unit in all_units]
        return generate_json_response_with_pulp_encoder(all_processed_units)


class ContentUnitUserMetadataResourceView(View):
    """
    This View allows users to read and write the pulp_user_metadata field on a particular
    content unit.
    """
    @auth_required(authorization.READ)
    def get(self, request, type_id, unit_id):
        """
        Return user metadata for a content unit.

        :param type_id: The Unit's type id.
        :type  type_id: basestring
        :param unit_id: The id of the unit that you wish to set the pulp_user_metadata field on
        :type  unit_id: basestring

        :return: response containing pulp user metadata field
        :rtype: django.http.HttpResponse or HttpResponseNotFound
        """
        cqm = factory.content_query_manager()
        try:
            unit = cqm.get_content_unit_by_id(type_id, unit_id)
        except MissingResource:
            msg = _('No content unit resource: %(r)s') % {'r': unit_id}
            return generate_json_response(msg, HttpResponseNotFound)

        resource = serial_content.content_unit_obj(
            unit[constants.PULP_USER_METADATA_FIELDNAME])
        return generate_json_response(resource)

    @auth_required(authorization.UPDATE)
    @parse_json_body()
    def put(self, request, type_id, unit_id):
        """
        Set the pulp_user_metadata field on a content unit.

        :param type_id: The Unit's type id.
        :type  type_id: basestring
        :param unit_id: The id of the unit that you wish to set the pulp_user_metadata field on
        :type  unit_id: basestring

        :return: response containing pulp user metadata_field
        :rtype: django.http.HttpResponse or HttpResponseNotFound
        """
        params = request.body_as_json
        cqm = factory.content_query_manager()
        try:
            cqm.get_content_unit_by_id(type_id, unit_id)
        except MissingResource:
            msg = _('No content unit resource: %(r)s') % {'r': unit_id}
            return generate_json_response(msg, HttpResponseNotFound)

        cm = factory.content_manager()
        delta = {constants.PULP_USER_METADATA_FIELDNAME: params}
        cm.update_content_unit(type_id, unit_id, delta)
        return generate_json_response(None)


class UploadsCollectionView(View):

    @auth_required(authorization.READ)
    def get(self, request):
        """
        Return a serialized response containing a dict with a list of upload_ids.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest

        :return: Serialized response containing a list of upload ids
        :rtype: django.http.HttpResponse
        """
        upload_manager = factory.content_upload_manager()
        upload_ids = upload_manager.list_upload_ids()
        return generate_json_response({'upload_ids': upload_ids})

    @auth_required(authorization.CREATE)
    @parse_json_body(allow_empty=True)
    def post(self, request, *args, **kwargs):
        """
        Initialize an upload and return a serialized dict containing the upload data.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :return : Serialized response containing a url to delete an upload and a unique id.
        :rtype : django.http.HttpResponse
        """
        upload_manager = factory.content_upload_manager()
        upload_id = upload_manager.initialize_upload()
        href = reverse('content_upload_resource', kwargs={'upload_id': upload_id})
        response = generate_json_response({'_href': href, 'upload_id': upload_id})
        response_redirect = generate_redirect_response(response, href)
        return response_redirect


class UploadSegmentResourceView(View):
    """
    Views for a single upload.
    """

    @auth_required(authorization.UPDATE)
    def put(self, request, upload_id, offset):
        """
        Upload to a specific file upload.

        :param request:   WSGI request object, body contains bits to upload
        :type  request:   django.core.handlers.wsgi.WSGIRequest
        :param upload_id: id of the initialized upload
        :type  upload_id: str
        :param offset:    place in the uploaded file to start writing
        :type  offset:    str of an integer
        :return:          response containing null
        :rtype:           django.http.HttpResponse

        :raises:          pulp.server.exceptions.MissingResource if upload ID does not exist
        :raises:          InvalidValue if offset cannot be converted to an integer
        """

        try:
            offset = int(offset)
        except ValueError:
            raise InvalidValue(['offset'])

        upload_manager = factory.content_upload_manager()

        # If the upload ID doesn't exists, either because it was not initialized
        # or was deleted, the call to the manager will raise missing resource
        upload_manager.save_data(upload_id, offset, request.body)
        return generate_json_response(None)


class UploadResourceView(View):
    """
    View for single upload
    """

    @auth_required(authorization.DELETE)
    def delete(self, request, upload_id):
        """
        Delete a single upload.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param upload_id: id of the upload to be deleted
        :type  upload_id: str

        :return: response with None
        :rtype: django.http.HttpResponse
        """
        upload_manager = factory.content_upload_manager()
        upload_manager.delete_upload(upload_id)
        return generate_json_response(None)


class ContentSourceCollectionView(View):
    """
    View for content sources.
    """

    @auth_required(authorization.READ)
    def get(self, request):
        """
        Get all content sources.

        :param request:   WSGI request object, body contains bits to upload
        :type  request:   django.core.handlers.wsgi.WSGIRequest

        :return: list of sources
        :rtype:  django.http.HttpResponse
        """
        container = ContentContainer()
        sources = []
        for source in container.sources.values():
            d = source.dict()
            link = {'_href': reverse('content_sources_resource',
                    kwargs={'source_id': source.id})}
            d.update(link)
            sources.append(d)
        return generate_json_response_with_pulp_encoder(sources)


class ContentSourceCollectionActionView(View):
    """
    View for actions on all sources.
    """

    @staticmethod
    def refresh(request):
        """
        Refresh all content sources

        :param request: WSGI request object, body contains bits to upload
        :type request: django.core.handlers.wsgi.WSGIRequest
        :raises: OperationPostponed when an async operation is performed
        """
        container = ContentContainer()
        content_sources = [tags.resource_tag(RESOURCE_CONTENT_SOURCE, id)
                           for id in container.sources.keys()]
        task_tags = [tags.action_tag(ACTION_REFRESH_ALL_CONTENT_SOURCES)] + content_sources
        task_result = content.refresh_content_sources.apply_async(tags=task_tags)
        raise OperationPostponed(task_result)

    @auth_required(authorization.UPDATE)
    @parse_json_body(allow_empty=True)
    def post(self, request, action):
        """
        Content source actions.

        :param request: WSGI request object, body contains bits to upload
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param action: Name of action to perform
        :type action: str
        """
        method = getattr(self, action, None)
        if method:
            return method(request)
        else:
            return HttpResponseBadRequest('bad request')


class ContentSourceResourceView(View):
    """
    View for single content source.
    """

    @auth_required(authorization.READ)
    def get(self, request, source_id):
        """
        Get a content source by ID.

        :param request:   WSGI request object, body contains bits to upload
        :type  request:   django.core.handlers.wsgi.WSGIRequest
        :param source_id: A content source ID.
        :type source_id: str

        :raises: MissingResource if source id does not exist
        :return: requested content source object.
        :rtype:  django.http.HttpResponse
        """
        container = ContentContainer()
        source = container.sources.get(source_id)
        if source:
            d = source.dict()
            link = {'_href': reverse('content_sources_resource',
                    kwargs={'source_id': source.id})}
            d.update(link)
            return generate_json_response_with_pulp_encoder(d)
        else:
            raise MissingResource(source_id=source_id)


class ContentSourceResourceActionView(View):
    """
    View for single content source actions.
    """

    @auth_required(authorization.UPDATE)
    @parse_json_body(allow_empty=True)
    def post(self, request, source_id, action):
        """
        Single content source actions.

        :param request:   WSGI request object, body contains bits to upload
        :type  request:   django.core.handlers.wsgi.WSGIRequest
        :param source_id: A content source ID.
        :type source_id: str
        :param action: Name of action to perform
        :type action: str
        :raises: MissingResource if source id does not exist
        """
        container = ContentContainer()
        source = container.sources.get(source_id)
        if source:
            method = getattr(self, action, None)
            if method:
                return method(request, source_id)
            else:
                return HttpResponseBadRequest('bad request')
        else:
            raise MissingResource(source_id=source_id)

    def refresh(self, request, content_source_id):
        """
        Refresh single content source

        :param request:   WSGI request object, body contains bits to upload
        :type  request:   django.core.handlers.wsgi.WSGIRequest
        :param content_source_id: A content source ID
        :type content_source_id: str
        :raises: OperationPostponed when an async operation is performed
        """
        task_tags = [tags.action_tag(ACTION_REFRESH_CONTENT_SOURCE),
                     tags.resource_tag(RESOURCE_CONTENT_SOURCE, content_source_id)]
        task_result = content.refresh_content_source.apply_async(
            tags=task_tags, kwargs={'content_source_id': content_source_id})
        raise OperationPostponed(task_result)
