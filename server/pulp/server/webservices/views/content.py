import json

from django.http import HttpResponse
from django.views.generic import View

from pulp.server.auth import authorization
from pulp.server.webservices.controllers.decorators import auth_required
from pulp.server.managers import factory


class UploadResourceView(View):
    """
    View for single upload
    """

    @auth_required(authorization.DELETE)
    def delete(self, request, upload_id, *args, **kwargs):
        """
        Delete a single upload.

        :param request  : WSGI request object
        :type  request  : WSGIRequest
        :param upload_id: id of the upload to be deleted
        :type  upload_id: string
        :return         : Serialized None
        :rtype          : HttpResponse
        """
        upload_manager = factory.content_upload_manager()
        upload_manager.delete_upload(upload_id)

        return HttpResponse(json.dumps(None), content_type='application/json')
