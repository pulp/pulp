import json

from django.http import HttpResponse
from django.views.generic import View

from pulp.common import tags
from pulp.server.auth import authorization
from pulp.server.exceptions import OperationPostponed
from pulp.server.managers import factory
from pulp.server.managers.content import orphan
from pulp.server.webservices.controllers.decorators import auth_required


class OrphanResourceView(View):
    """
    Views for a specific orphan.
    """
    @auth_required(authorization.READ)
    def get(self, request, content_type, unit_id, *args, **kwargs):
        """
        Return a serialized object representing the requested orphan

        :param request: WSGI request object
        :type  request: WSGIRequest
        :param content_type: content type of the requested orphan
        :type  content_type: string
        :param unit_id: id of the requested unit
        :type         : string
        :return       : Serialized object representing the requested orphan
        :rtype        : HttpResponse
        """
        orphan_manager = factory.content_orphan_manager()
        orphan_dict = orphan_manager.get_orphan(content_type, unit_id)
        orphan_dict['_href'] = request.get_full_path()

        return HttpResponse(json.dumps(orphan_dict), content_type='application/json')

    @auth_required(authorization.DELETE)
    def delete(self, request, content_type, unit_id, *args, **kwargs):
        """
        Delete a specified orphan.

        :param request     : WSGI request object
        :type  request     : WSGIRequst
        :param content_type: content type of the requested orphan
        :type  content_type: string
        :param unit_id     : id of the requested orphan
        :type  unit_id     : string
        :raises            : OperationPostponed
        """
        unit_info = [{'content_type_id': content_type, 'unit_id': unit_id}]
        task_tags = [tags.resource_tag(tags.RESOURCE_CONTENT_UNIT_TYPE, 'orphans')]
        async_task = orphan.delete_orphans_by_id.apply_async((unit_info,), tags=task_tags)
        raise OperationPostponed(async_task)
