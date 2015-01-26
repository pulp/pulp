from django.views.generic import View

from pulp.server.auth import authorization
from pulp.server.exceptions import InvalidValue
from pulp.server.managers import factory
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
