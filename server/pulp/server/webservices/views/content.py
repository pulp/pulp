from gettext import gettext as _
import json

from django.core.urlresolvers import reverse
from django.http import HttpResponseNotFound, HttpResponseRedirect
from django.views.generic import View

from pulp.common import tags
from pulp.server.auth import authorization
from pulp.server.db.model.criteria import Criteria
from pulp.server.exceptions import InvalidValue, MissingResource, OperationPostponed
from pulp.server.managers import factory
from pulp.server.managers.content import orphan as content_orphan
from pulp.server.webservices import serialization
from pulp.server.webservices.controllers.decorators import auth_required
from pulp.server.webservices.views.util import (generate_json_response,
                                                generate_json_response_with_pulp_encoder)


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
        """
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


class ContentTypeResourceView(View):
    """
    View for a single content type.
    """

    @auth_required(authorization.READ)
    def get(self, request, type_id):
        """
        Return a response containing a dict with info about a content type.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param type_id: type of content unit
        :type  type_id: str

        :return: response containing a dict that contains info about a content type or
                 404 response if the specified content type is not found.
        :rtype : django.http.HttpResponse or HttpResponseNotFound
        """
        cqm = factory.content_query_manager()
        content_type = cqm.get_content_type(type_id)
        if content_type is None:
            msg = _('No content type resource: %(r)s') % {'r': type_id}
            return generate_json_response(msg, response_class=HttpResponseNotFound)
        resource = serialization.content.content_type_obj(content_type)
        # These urls are not valid endpoints but are left here for for semantic versioning.
        # BZ - 1187287
        links = {
            'actions': {'_href': '/'.join([request.get_full_path().rstrip('/'), 'actions/'])},
            'content_units': {'_href': '/'.join([request.get_full_path().rstrip('/'), 'units/'])}
        }
        resource.update(links)
        return generate_json_response_with_pulp_encoder(resource)


class ContentTypesView(View):
    """
    View for all content types.
    """

    @auth_required(authorization.READ)
    def get(self, request):
        """
        Returns a response continaing a list of dicts, one for each available content type.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest

        :return: response containing a serialized list dicts, one for each content type
        :rtype : django.http.HttpResponse
        """
        collection = []
        cqm = factory.content_query_manager()
        type_ids = cqm.list_content_types()
        for type_id in type_ids:
            link = {'_href': reverse('content_type_resource', kwargs={'type_id': type_id})}
            link.update({'content_type': type_id})
            collection.append(link)
        return generate_json_response(collection)


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

        resource = serialization.content.content_unit_obj(unit)
        resource.update({'children': serialization.content.content_unit_child_link_objs(resource)})
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
        all_processed_units = []
        for unit in all_units:
            unit = serialization.content.content_unit_obj(unit)
            unit.update({'_href': '/'.join([request.get_full_path().rstrip('/'),
                                            unit['_id'], ''])})
            unit.update({'children': serialization.content.content_unit_child_link_objs(unit)})
            all_processed_units.append(unit)

        return generate_json_response_with_pulp_encoder(all_processed_units)


class UploadsCollectionView(View):

    @auth_required(authorization.READ)
    def get(self, request):
        """
        Return a serialized response containing a dict with a list of upload_ids.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest

        :return: Serialized response containing a list  of upload ids
        :rtype: django.http.HttpResponse
        """
        upload_manager = factory.content_upload_manager()
        upload_ids = upload_manager.list_upload_ids()
        return generate_json_response({'upload_ids': upload_ids})

    @auth_required(authorization.CREATE)
    def post(self, request, *args, **kwargs):
        """
        Initialize an upload and return a serialized dict conaining the upload data.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :return       : Serialized response containing a url to delete an upload and a unique id.
        :rtype        : HttpResponseRedirect
        """
        upload_manager = factory.content_upload_manager()
        upload_id = upload_manager.initialize_upload()
        href = reverse('content_upload_resource', kwargs={'upload_id': upload_id})
        return HttpResponseRedirect(
            redirect_to=href,
            status=201,
            reason="Created",
            content=json.dumps({'_href': href, 'upload_id': upload_id}),
            content_type="application/json"
        )


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
