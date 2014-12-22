from django.views.generic import View

from pulp.common import tags
from pulp.server.auth import authorization
from pulp.server.exceptions import InvalidValue, OperationPostponed
from pulp.server.managers import factory
from pulp.server.managers.content import orphan
from pulp.server.webservices.controllers.decorators import auth_required
from pulp.server.webservices.views.util import (generate_json_response,
                                                generate_json_response_with_pulp_encoder)


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
        :type  upload_id: string
        :param offset:    place in the uploaded file to start writing
        :type  offset:    string of an integer
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
        :return       : response containing a dict that itself contains a dict for each orphan.
        :rtype        : django.http.HttpResponse
        """
        orphan_manager = factory.content_orphan_manager()

        # convert the counts into sub-documents so we can add _href fields to them
        # add links to the content type sub-collections
        rest_summary = {}
        for key, value in orphan_manager.orphans_summary().items():
            rest_summary[key] = {
                'count': value,
                '_href': '/'.join([request.get_full_path().rstrip('/'), key]) + '/'
            }

        return generate_json_response(rest_summary)

    @auth_required(authorization.DELETE)
    def delete(self, request):
        """
        Delete all orphaned units and raise OperationPostponed

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :raises       : OperationPostponed
        """
        task_tags = [tags.resource_tag(tags.RESOURCE_CONTENT_UNIT_TYPE, 'orphans')]
        async_task = orphan.delete_all_orphans.apply_async(tags=task_tags)
        raise OperationPostponed(async_task)
