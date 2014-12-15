import json

from django.views.generic import View
from django.http import HttpResponse, HttpResponseRedirect

from pulp.server.auth import authorization
from pulp.server.managers import factory
from pulp.server.webservices import serialization
from pulp.server.webservices.controllers.decorators import auth_required


class UploadsCollectionView(View):

    # Scope: Collection
    # GET:   Retrieve all upload request IDs
    # POST:  Create a new upload request (and return the ID)

    @auth_required(authorization.READ)
    def get(self, request, *args, **kwargs):

        upload_manager = factory.content_upload_manager()
        upload_ids = upload_manager.list_upload_ids()
        return HttpResponse(json.dumps({'upload_ids': upload_ids}), content_type="application/json")
    #

    # @auth_required(authorization.CREATE)
    def post(self, request, *args, **kwargs):
        import pydevd
        pydevd.settrace('localhost', port=34567, stdoutToServer=True, stderrToServer=True)
        upload_manager = factory.content_upload_manager()
        upload_id = upload_manager.initialize_upload()
        # location = serialization.link.child_link_obj(upload_id)
        href = '/'.join([request.get_full_path().rstrip('/'), upload_id]) + '/'
        response = HttpResponseRedirect(
            redirect_to=href,
            status=201,
            reason="Created",
            content=json.dumps({'_href': href, 'upload_id': upload_id}),
            content_type="application/json"
        )
        response.__setitem__('Location', "anothertest")
        #
        return response