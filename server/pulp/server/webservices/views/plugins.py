from django.views.generic import View

from pulp.server.auth import authorization
from pulp.server.managers import factory
from pulp.server.webservices.controllers.decorators import auth_required
from pulp.server.webservices.views.util import (generate_json_response,
                                                generate_json_response_with_pulp_encoder)


class DistributorResourceView(View):
    pass


class DistributorsView(View):
    pass


class ImporterResourceView(View):
    pass


class ImportersView(View):
    pass


class TypeResourceView(View):
    pass


class TypesView(View):
    """
    View for dealing with all plugin types.
    """

    @auth_required(authorization.READ)
    def get(self, request):
        """
        Get all type definitions

        :param request: WSGI Request obect
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :return       : Serialized list of objects representing all available content types
        :rtype        : HttpResponse
        """
        manager = factory.plugin_manager()
        type_defs = manager.types()

        for type_definition in type_defs:
            href = {'_href': '/'.join([request.get_full_path().rstrip('/'),
                                       type_definition['id'], ''])}
            type_definition.update(href)

        return generate_json_response_with_pulp_encoder(type_defs)
