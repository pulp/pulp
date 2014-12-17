import json

from django.http import HttpResponse
from django.views.generic import View

from pulp.server.auth import authorization
from pulp.server.webservices.controllers.decorators import auth_required
from pulp.server.managers import factory


class UploadResourceView(View):

    # Scope:  Resource
    # DELETE: Delete an uploaded file

    @auth_required(authorization.DELETE)
    def delete(self, request, upload_id, *args, **kwargs):
        upload_manager = factory.content_upload_manager()
        upload_manager.delete_upload(upload_id)

        return HttpResponse(json.dumps(None), content_type='application/json')