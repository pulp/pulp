import json

from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic import View

from pulp.server.auth import authorization
from pulp.server.managers import factory
from pulp.server.webservices.controllers.decorators import auth_required


class UploadsCollectionView(View):

    @auth_required(authorization.READ)
    def get(self, request, *args, **kwargs):
        """
        Return a serialized response containing a dict with a list of upload_ids.

        :param request: WSGI request object
        :type  request: WSGIRequest
        :return       : Serialized response containing a list  of upload ids
        :rtype        : HttpResponse
        """

        upload_manager = factory.content_upload_manager()
        upload_ids = upload_manager.list_upload_ids()
        return HttpResponse(json.dumps({'upload_ids': upload_ids}), content_type="application/json")
    #

    @auth_required(authorization.CREATE)
    def post(self, request, *args, **kwargs):
        """
        Initialize an upload and return a serialized dictionary containing a url and
        the unique upload id.

        :param request: WSGI request object
        :type  request: WSGIRequest
        :return       : Serialized response containing a url (unused) and a unique upload id
        :rtype        : HttpResponseRedirect
        """
        upload_manager = factory.content_upload_manager()
        upload_id = upload_manager.initialize_upload()
        href = '/'.join([request.get_full_path().rstrip('/'), upload_id]) + '/'
        return HttpResponseRedirect(
            redirect_to=href,
            status=201,
            reason="Created",
            content=json.dumps({'_href': href, 'upload_id': upload_id}),
            content_type="application/json"
        )