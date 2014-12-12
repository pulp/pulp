from gettext import gettext as _
import json

from django.http import HttpResponse, HttpResponseNotFound
from django.views.generic import View
from django.core.urlresolvers import reverse

from pulp.server.db.model.criteria import Criteria
from pulp.server.exceptions import MissingResource
from pulp.server.managers import factory
from pulp.server.webservices import serialization
from pulp.server.webservices.controllers.base import json_encoder as pulp_json_encoder


class ContentUnitResourceView(View):

    # @auth_required(authorization.READ)
    def get(self, request, *args, **kwargs):
        """
        Return information about a content unit.
        """

        type_id = kwargs.get('type_id')
        unit_id = kwargs.get('unit_id')
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
