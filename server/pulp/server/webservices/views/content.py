import json

from django.views.generic import View
from django.http import HttpResponse

from pulp.common import tags
from pulp.server.auth import authorization
from pulp.server.exceptions import OperationPostponed
from pulp.server.managers import factory
from pulp.server.managers.content import orphan
from pulp.server.webservices.controllers.decorators import auth_required


class OrphanTypeSubCollectionView(View):

    @auth_required(authorization.READ)
    def get(self, request, content_type, *args, **kwargs):
        orphan_manager = factory.content_orphan_manager()
        orphans = list(orphan_manager.generate_orphans_by_type_with_unit_keys(content_type))

        for orphan_dict in orphans:
            orphan_dict['_href'] = '/'.join([request.get_full_path().rstrip('/'), orphan_dict['_id'], ''])

        return HttpResponse(json.dumps(orphans), content_type='application/json')

    @auth_required(authorization.DELETE)
    def delete(self, request, content_type, *args, **kwargs):
        task_tags = [tags.resource_tag(tags.RESOURCE_CONTENT_UNIT_TYPE, 'orphans')]
        async_task = orphan.delete_orphans_by_type.apply_async((content_type,), tags=task_tags)
        raise OperationPostponed(async_task)
