import json

from django.http import HttpResponse
from django.views.generic import View

from pulp.server.auth import authorization
from pulp.server.managers import factory
from pulp.server.webservices.controllers.decorators import auth_required


class CatalogResourceView(View):
    """
    Views for the catalog by source_id.
    """

    @auth_required(authorization.DELETE)
    def delete(self, request, source_id, *args, **kwargs):
        """
        Delete entries from the catlog by content source id

        :param request  : WSGI request object
        :type  request  : WSGIRequest
        :param source_id: id of source whose content should be deleted
        :type  source_id: string
        :return         : Serialized output containing the number if items deleted
        :rtype          : HttpResponse
        """
        manager = factory.content_catalog_manager()
        purged = manager.purge(source_id)
        deleted = dict(deleted=purged)
        return HttpResponse(json.dumps(deleted), content_type='application/json')

