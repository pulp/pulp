from django.views.generic import View

from pulp.common import tags
from pulp.server.auth import authorization
from pulp.server.exceptions import OperationPostponed
from pulp.server.managers.content import orphan as orphan_manager
from pulp.server.webservices.controllers.decorators import auth_required


class DeleteOrphansActionView(View):

    @auth_required(authorization.DELETE)
    def post(self, request, *args, **kwargs):
        """
        Pass the appropriate tags and json object to delete_orphans_by_id.
        Raises an OperationPostponed.

        :param request: WSGI request object
        :type  request: WSGIRequest
        """
        orphans = request.body_as_json
        task_tags = [tags.action_tag('delete_orphans'),
                     tags.resource_tag(tags.RESOURCE_CONTENT_UNIT_TYPE, 'orphans')]
        async_task = orphan_manager.delete_orphans_by_id.apply_async([orphans], tags=task_tags)
        raise OperationPostponed(async_task)
