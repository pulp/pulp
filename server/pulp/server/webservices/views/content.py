from gettext import gettext as _
import json

from django.http import HttpResponse, HttpResponseNotFound
from django.views.generic import View

from pulp.server.auth import authorization
from pulp.server.exceptions import MissingResource
from pulp.server.managers import factory
from pulp.server.webservices import serialization
from pulp.server.webservices.controllers.base import json_encoder as pulp_json_encoder
from pulp.server.webservices.controllers.decorators import auth_required


class ContentUnitResourceView(View):

    @auth_required(authorization.READ)
    def get(self, request, type_id, unit_id, *args, **kwargs):
        """
        Return information about a content unit.

        :param request: WSGI request object
        :type  request: WSGIRequest
        :param type_id: type of content contained in the repo
        :type  type_id: unicode string
        :param unit_id: unique id of a unit
        :type  unit_id: unicode string
        :return       : Serialized metadata for requested unit
        :rtype        : JSON
        """
        cqm = factory.content_query_manager()
        try:
            unit = cqm.get_content_unit_by_id(type_id, unit_id)
        except MissingResource:
            return HttpResponseNotFound(
                json.dumps(_('No content unit resource: %(r)s') % {'r': unit_id}),
                content_type="application/json"
            )
        resource = serialization.content.content_unit_obj(unit)
        resource.update({'children': serialization.content.content_unit_child_link_objs(resource)})
        return HttpResponse(json.dumps(resource, default=pulp_json_encoder),
                            content_type="application/json")
