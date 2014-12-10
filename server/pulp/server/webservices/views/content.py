from gettext import gettext as _
import json

from django.http import HttpResponse, HttpResponseNotFound
from django.views.generic import View
from django.core.urlresolvers import reverse

from pulp.server.db.model.criteria import Criteria
from pulp.server.managers import factory
from pulp.server.webservices import serialization
from pulp.server.webservices.controllers.base import json_encoder as pulp_json_encoder


class ContentTypesView(View):
    # @auth_required(authorization.READ)
    def get(self, request, *args, **kwargs):
        """
        List the available content types.
        """
        collection = []
        cqm = factory.content_query_manager()
        type_ids = cqm.list_content_types()
        for type_id in type_ids:
            link = {'_href': reverse('content_type_resource', kwargs={'type_id': type_id})}
            link.update({'content_type': type_id})
            collection.append(link)
        return HttpResponse(json.dumps(collection), content_type="application/json")


class ContentTypeResourceView(View):
    # @auth_required(authorization.READ)
    def get(self, request, *args, **kwargs):
        """
        Return information about a content type. Requires type_id to be
        passed as a keyword argument.
        """
        type_id = kwargs.get('type_id')
        cqm = factory.content_query_manager()
        content_type = cqm.get_content_type(type_id)
        if content_type is None:
            return HttpResponseNotFound(
                json.dumps(_('No content type resource: %(r)s') % {'r': type_id}),
                content_type="application/json"
            )
        resource = serialization.content.content_type_obj(content_type)
        links = {
            # TODO(asmacdo) replace with reverse url lookup.
            # Well, maybe not. i think these must be plugin api endpoints...
            'actions': {'_href': '/'.join([request.get_full_path().rstrip('/'), 'actions/'])},
            'content_units': {'_href': '/'.join([request.get_full_path().rstrip('/'), 'units/'])}
        }
        resource.update(links)
        return HttpResponse(json.dumps(resource, default=pulp_json_encoder),
                            content_type="application/json")


class ContentUnitsCollectionView(View):
    @staticmethod
    def process_unit(unit, request):
        # TODO (bmbouter) this function could probably be included in the base SearchAPIView
        unit = serialization.content.content_unit_obj(unit)
        # TODO(asmacdo) replace with reverseurl lookup
        unit.update({'_href': '/'.join([request.get_full_path().rstrip('/'), unit['_id'] + '/'])})
        unit.update({'children': serialization.content.content_unit_child_link_objs(unit)})
        return unit

    # @auth_required(authorization.READ)
    def get(self, request, *args, **kwargs):
        """
        List all the available content units.
        """
        type_id = kwargs.get('type_id')

        cqm = factory.content_query_manager()
        units = cqm.find_by_criteria(type_id, Criteria())
        return HttpResponse(json.dumps([self.process_unit(unit, request) for unit in units],
                                       default=pulp_json_encoder), content_type="application/json")
