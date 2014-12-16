from gettext import gettext as _
import json

from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseNotFound
from django.views.generic import View

from pulp.server.auth import authorization
from pulp.server.db.model.criteria import Criteria
from pulp.server.managers import factory
from pulp.server.webservices import serialization
from pulp.server.webservices.controllers.base import json_encoder as pulp_json_encoder
from pulp.server.webservices.controllers.decorators import auth_required


class ContentTypesView(View):

    @auth_required(authorization.READ)
    def get(self, request, *args, **kwargs):
        """
        List the available content types.

        :param request: WSGI request object
        :type  request: WSGIRequest
        :return       : Serialized response containing a list of the content types
        :rtype        : HttpResponse
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

    @auth_required(authorization.READ)
    def get(self, request, type_id, *args, **kwargs):
        """
        Return information about a content type. Requires type_id to be
        passed as a keyword argument.

        :param request: WSGI request object
        :type  request: WSGIRequest
        :type_id      : type of content unit
        :type type_id : unicode
        :return       : Serialized response containing information about the given content type or
                        a HttpResponseNotFound response if the specified content type is not found.
        :rtype        : HttpResponse or HttpResponseNotFound
        """
        cqm = factory.content_query_manager()
        content_type = cqm.get_content_type(type_id)
        if content_type is None:
            return HttpResponseNotFound(
                json.dumps(_('No content type resource: %(r)s') % {'r': type_id}),
                content_type="application/json"
            )
        resource = serialization.content.content_type_obj(content_type)
        links = {
            'actions': {'_href': '/'.join([request.get_full_path().rstrip('/'), 'actions/'])},
            'content_units': {'_href': '/'.join([request.get_full_path().rstrip('/'), 'units/'])}
        }
        resource.update(links)
        return HttpResponse(json.dumps(resource, default=pulp_json_encoder),
                            content_type="application/json")


class ContentUnitsCollectionView(View):

    @staticmethod
    def process_unit(unit, request):
        """
        Create a dictionary that contains a url with for a given id and any
        children that the unit has.

        :param unit   : metadata about a unit
        :type  unit   : dictionary
        :param request: WSGI request object
        :type  request: WSGIRequest
        :return       : serialized unit with url and children
        :rtype        : dictionary
        """
        unit = serialization.content.content_unit_obj(unit)
        unit.update({'_href': '/'.join([request.get_full_path().rstrip('/'), unit['_id'] + '/'])})
        unit.update({'children': serialization.content.content_unit_child_link_objs(unit)})
        return unit

    @auth_required(authorization.READ)
    def get(self, request, type_id, *args, **kwargs):
        """
        List the available content units

        :param request: WSGI request object
        :type  request: WSGIRequest
        :type_id      : type of content unit
        :type type_id : unicode
        :return       : Serialized response containing a list of the available content units of
                        of type type_id
        :rtype        : HttpResponse
        """
        cqm = factory.content_query_manager()
        units = cqm.find_by_criteria(type_id, Criteria())
        return HttpResponse(json.dumps([self.process_unit(unit, request) for unit in units],
                                       default=pulp_json_encoder), content_type="application/json")
